"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TradingMode(str, Enum):
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"
    FULL_AUTO_PLUS = "full_auto_plus"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class StrategyType(str, Enum):
    LONDON_OPEN_BREAKOUT = "london_open_breakout"
    SMA_CROSSOVER = "sma_crossover"
    AI_SCANNER = "ai_scanner"
    MANUAL = "manual"


class Trade(BaseModel):
    id: str
    symbol: str
    direction: TradeDirection
    contracts: int
    entry_price: float
    current_price: Optional[float] = None
    stop_loss: float
    take_profit: float
    strategy: StrategyType
    status: TradeStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


class RiskSettings(BaseModel):
    stop_loss_pct: float = Field(default=0.5, ge=0.1, le=5.0)
    take_profit_ratio: float = Field(default=2.0, ge=1.0, le=10.0)
    max_contracts: int = Field(default=3, ge=1, le=20)
    max_daily_loss_usd: float = Field(default=200.0, ge=10.0)
    max_open_trades: int = Field(default=3, ge=1, le=10)
    trade_size_usd: float = Field(default=500.0, ge=100.0)


class UpdateRiskRequest(BaseModel):
    stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=5.0)
    take_profit_ratio: Optional[float] = Field(None, ge=1.0, le=10.0)
    max_contracts: Optional[int] = Field(None, ge=1, le=20)
    max_daily_loss_usd: Optional[float] = Field(None, ge=10.0)
    max_open_trades: Optional[int] = Field(None, ge=1, le=10)
    trade_size_usd: Optional[float] = Field(None, ge=100.0)


class TradeTarget(BaseModel):
    symbol: str
    name: Optional[str] = None
    asset_type: Optional[str] = "futures"
    enabled: bool = True
    added_at: datetime = Field(default_factory=datetime.utcnow)
    current_price: Optional[float] = None
    daily_change_pct: Optional[float] = None


class AddTargetRequest(BaseModel):
    symbol: str
    name: Optional[str] = None
    asset_type: Optional[str] = "futures"


class PnLSummary(BaseModel):
    today_pnl: float = 0.0
    today_pnl_pct: float = 0.0
    open_pnl: float = 0.0
    total_trades_today: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    daily_loss_limit: float = 200.0
    daily_loss_used_pct: float = 0.0
    shutdown_triggered: bool = False


class BotStatus(BaseModel):
    is_running: bool
    mode: TradingMode
    open_trades_count: int
    pnl: PnLSummary
    last_signal: Optional[str] = None
    last_signal_time: Optional[datetime] = None
    scanner_active: bool
    targets_count: int
    uptime_seconds: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModeChangeRequest(BaseModel):
    mode: TradingMode


class BotCommandRequest(BaseModel):
    command: str
    params: Optional[dict] = None


class ScanResult(BaseModel):
    symbol: str
    score: float = Field(ge=0.0, le=100.0)
    strategy: StrategyType
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: str
    reason: str
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    approved: Optional[bool] = None


class NotificationType(str, Enum):
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    DAILY_LIMIT = "daily_limit"
    SCANNER_SIGNAL = "scanner_signal"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    ERROR = "error"


class Notification(BaseModel):
    id: str
    type: NotificationType
    title: str
    body: str
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False
