"""
Configuration - reads from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Security
    API_SECRET: Optional[str] = None

    # Coinbase Advanced Trade API
    COINBASE_API_KEY: Optional[str] = None
    COINBASE_API_SECRET: Optional[str] = None
    COINBASE_SANDBOX: bool = True

    # Alpaca (for stocks/ETFs)
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_API_SECRET: Optional[str] = None
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    # Trading defaults
    DEFAULT_STOP_LOSS_PCT: float = 0.5
    DEFAULT_TAKE_PROFIT_RATIO: float = 2.0
    DEFAULT_MAX_CONTRACTS: int = 3
    DEFAULT_MAX_DAILY_LOSS: float = 200.0
    DEFAULT_TRADE_SIZE_USD: float = 500.0

    # Scanner settings
    SCAN_INTERVAL_SECONDS: int = 60
    MIN_SCORE_FOR_TRADE: float = 70.0

    class Config:
        env_file = ".env"


settings = Settings()
