"""
Risk Manager
"""

import logging
from datetime import datetime, date
from typing import Optional

from models import RiskSettings, UpdateRiskRequest
from config import settings

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self):
        self.settings = RiskSettings(
            stop_loss_pct=settings.DEFAULT_STOP_LOSS_PCT,
            take_profit_ratio=settings.DEFAULT_TAKE_PROFIT_RATIO,
            max_contracts=settings.DEFAULT_MAX_CONTRACTS,
            max_daily_loss_usd=settings.DEFAULT_MAX_DAILY_LOSS,
            trade_size_usd=settings.DEFAULT_TRADE_SIZE_USD,
        )
        self._daily_loss: float = 0.0
        self._daily_loss_date: date = date.today()
        self._shutdown_triggered: bool = False

    def _reset_if_new_day(self):
        today = date.today()
        if today != self._daily_loss_date:
            self._daily_loss = 0.0
            self._daily_loss_date = today
            self._shutdown_triggered = False

    def record_trade_result(self, pnl: float):
        self._reset_if_new_day()
        self._daily_loss += pnl
        if self._daily_loss <= -self.settings.max_daily_loss_usd:
            self._shutdown_triggered = True
        return self._shutdown_triggered

    @property
    def should_shutdown(self) -> bool:
        self._reset_if_new_day()
        return self._shutdown_triggered

    @property
    def daily_pnl(self) -> float:
        self._reset_if_new_day()
        return self._daily_loss

    @property
    def daily_loss_used_pct(self) -> float:
        if self.settings.max_daily_loss_usd == 0:
            return 0.0
        used = abs(min(self._daily_loss, 0))
        return min((used / self.settings.max_daily_loss_usd) * 100, 100.0)

    def can_open_trade(self, open_trade_count: int) -> tuple[bool, str]:
        if self.should_shutdown:
            return False, "Daily loss limit reached"
        if open_trade_count >= self.settings.max_open_trades:
            return False, f"Max open trades reached"
        return True, "OK"

    def calculate_stop_loss(self, entry_price: float, direction: str) -> float:
        sl_amount = entry_price * (self.settings.stop_loss_pct / 100)
        if direction == "long":
            return round(entry_price - sl_amount, 4)
        else:
            return round(entry_price + sl_amount, 4)

    def calculate_take_profit(self, entry_price: float, stop_loss: float, direction: str) -> float:
        risk = abs(entry_price - stop_loss)
        reward = risk * self.settings.take_profit_ratio
        if direction == "long":
            return round(entry_price + reward, 4)
        else:
            return round(entry_price - reward, 4)

    def calculate_contracts(self, entry_price: float, contract_value: float = 100.0) -> int:
        if contract_value <= 0:
            return 1
        contracts = int(self.settings.trade_size_usd / (entry_price * contract_value / 100))
        return max(1, min(contracts, self.settings.max_contracts))

    def get_settings(self) -> dict:
        return {
            **self.settings.dict(),
            "daily_pnl": self._daily_loss,
            "daily_loss_used_pct": self.daily_loss_used_pct,
            "shutdown_triggered": self._shutdown_triggered,
        }

    def update_settings(self, request: UpdateRiskRequest):
        data = request.dict(exclude_none=True)
        for key, val in data.items():
            setattr(self.settings, key, val)
        if "max_daily_loss_usd" in data and self._shutdown_triggered:
            if abs(self._daily_loss) < self.settings.max_daily_loss_usd:
                self._shutdown_triggered = False
