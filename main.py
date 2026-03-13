"""
Trading Bot Backend - FastAPI Server
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models import BotStatus, TradingMode, ModeChangeRequest, UpdateRiskRequest, AddTargetRequest
from risk_manager import RiskManager
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead.append(connection)
        for conn in dead:
            self.active_connections.remove(conn)


manager = ConnectionManager()
risk_manager = RiskManager()
security = HTTPBearer(auto_error=False)

is_running = False
trading_mode = TradingMode.MANUAL
start_time = None
open_trades = []
trade_history = []
targets = [{"symbol": "NOL", "name": "Nano Crude Oil", "asset_type": "futures", "enabled": True}]


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if settings.API_SECRET and (not credentials or credentials.credentials != settings.API_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Trading Bot Backend starting...")
    yield
    logger.info("Shutting down...")


app = FastAPI(title="NEXUS-FINBOT API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/status")
async def get_status(_=Depends(verify_token)):
    uptime = None
    if start_time:
        uptime = (datetime.utcnow() - start_time).total_seconds()
    return {
        "is_running": is_running,
        "mode": trading_mode.value,
        "open_trades_count": len(open_trades),
        "targets_count": len(targets),
        "uptime_seconds": uptime,
        "scanner_active": trading_mode in (TradingMode.FULL_AUTO, TradingMode.FULL_AUTO_PLUS),
        "pnl": {
            "today_pnl": risk_manager.daily_pnl,
            "daily_loss_used_pct": risk_manager.daily_loss_used_pct,
            "shutdown_triggered": risk_manager.should_shutdown,
            "daily_loss_limit": risk_manager.settings.max_daily_loss_usd,
            "open_pnl": 0.0,
            "total_trades_today": len(trade_history),
            "winning_trades": len([t for t in trade_history if (t.get("pnl") or 0) > 0]),
            "losing_trades": len([t for t in trade_history if (t.get("pnl") or 0) <= 0]),
            "win_rate": 0.0,
            "today_pnl_pct": 0.0,
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/bot/start")
async def start_bot(_=Depends(verify_token)):
    global is_running, start_time
    if risk_manager.should_shutdown:
        raise HTTPException(status_code=400, detail="Daily loss limit reached")
    is_running = True
    start_time = datetime.utcnow()
    await manager.broadcast({"event": "bot_started", "timestamp": datetime.utcnow().isoformat()})
    return {"message": "Bot started", "running": True}


@app.post("/bot/stop")
async def stop_bot(_=Depends(verify_token)):
    global is_running
    is_running = False
    await manager.broadcast({"event": "bot_stopped", "timestamp": datetime.utcnow().isoformat()})
    return {"message": "Bot stopped", "running": False}


@app.post("/bot/mode")
async def set_mode(request: ModeChangeRequest, _=Depends(verify_token)):
    global trading_mode
    trading_mode = request.mode
    await manager.broadcast({"event": "mode_changed", "mode": request.mode.value})
    return {"message": f"Mode set to {request.mode.value}", "mode": request.mode.value}


@app.get("/trades/open")
async def get_open_trades(_=Depends(verify_token)):
    return {"trades": open_trades}


@app.get("/trades/history")
async def get_trade_history(limit: int = 50, _=Depends(verify_token)):
    return {"trades": trade_history[-limit:]}


@app.get("/trades/pnl")
async def get_pnl(_=Depends(verify_token)):
    return {
        "today_pnl": risk_manager.daily_pnl,
        "daily_loss_used_pct": risk_manager.daily_loss_used_pct,
        "shutdown_triggered": risk_manager.should_shutdown,
    }


@app.get("/targets")
async def get_targets(_=Depends(verify_token)):
    return {"targets": targets}


@app.post("/targets")
async def add_target(request: AddTargetRequest, _=Depends(verify_token)):
    target = {"symbol": request.symbol.upper(), "name": request.name, "asset_type": request.asset_type, "enabled": True}
    targets.append(target)
    return {"message": f"Target {request.symbol.upper()} added", "target": target}


@app.delete("/targets/{symbol}")
async def remove_target(symbol: str, _=Depends(verify_token)):
    global targets
    targets = [t for t in targets if t["symbol"] != symbol.upper()]
    return {"message": f"Target {symbol.upper()} removed"}


@app.get("/risk")
async def get_risk(_=Depends(verify_token)):
    return risk_manager.get_settings()


@app.put("/risk")
async def update_risk(request: UpdateRiskRequest, _=Depends(verify_token)):
    risk_manager.update_settings(request)
    await manager.broadcast({"event": "risk_updated"})
    return {"message": "Risk settings updated", "settings": risk_manager.get_settings()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await websocket.send_json({
        "event": "init",
        "is_running": is_running,
        "mode": trading_mode.value,
        "timestamp": datetime.utcnow().isoformat()
    })
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
