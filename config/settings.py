"""
إعدادات المشروع الرئيسية
Project Settings Configuration
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """الإعدادات الرئيسية للمشروع"""
    
    # General
    APP_NAME: str = "Golden-AI Pro"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = Field(default="postgresql://postgres:password@localhost:5432/golden_ai", env="DATABASE_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # MT5 Configuration
    MT5_ENABLED: bool = Field(default=True, env="MT5_ENABLED")
    MT5_PATH: Optional[str] = Field(default=None, env="MT5_PATH")
    MT5_ACCOUNT: Optional[int] = Field(default=None, env="MT5_ACCOUNT")
    MT5_PASSWORD: Optional[str] = Field(default=None, env="MT5_PASSWORD")
    MT5_SERVER: Optional[str] = Field(default=None, env="MT5_SERVER")
    
    # ZeroMQ Configuration (Alternative MT5 Connection)
    ZMQ_ENABLED: bool = True
    ZMQ_HOST: str = "localhost"
    ZMQ_PORT: int = 15555
    ZMQ_TIMEOUT: int = 5000
    
    # Trading Configuration
    SYMBOL: str = "XAUUSD"
    TIMEFRAMES: List[str] = ["M1", "M5", "M15", "H1", "H4", "D1"]
    PRIMARY_TIMEFRAME: str = "H1"
    
    # Risk Management
    MAX_RISK_PER_TRADE: float = 0.02  # 2%
    MAX_DAILY_DRAWDOWN: float = 0.05  # 5%
    MAX_TOTAL_DRAWDOWN: float = 0.20  # 20%
    DEFAULT_STOP_LOSS: float = 50.0   # pips
    DEFAULT_TAKE_PROFIT: float = 100.0  # pips
    USE_TRAILING_STOP: bool = True
    TRAILING_STOP_ACTIVATION: float = 30.0  # pips
    TRAILING_STOP_DISTANCE: float = 20.0    # pips
    
    # AI Model Configuration
    MODEL_UPDATE_INTERVAL: int = 24  # hours
    PREDICTION_THRESHOLD: float = 0.65
    CONFIDENCE_THRESHOLD: float = 0.70
    ENSEMBLE_WEIGHTS: dict = {
        "lstm_attention": 0.4,
        "transformer": 0.35,
        "xgboost": 0.25
    }
    
    # SMC Configuration
    SMC_LOOKBACK: int = 100
    OB_MIN_CANDLES: int = 3
    FVG_MIN_SIZE: float = 0.5  # pips for XAUUSD
    LIQUIDITY_RANGE_PERCENT: float = 0.01
    
    # Kill Zones (UTC Times)
    LONDON_KILL_ZONE_START: str = "07:00"
    LONDON_KILL_ZONE_END: str = "10:00"
    NY_KILL_ZONE_START: str = "12:00"
    NY_KILL_ZONE_END: str = "15:00"
    ASIAN_KILL_ZONE_START: str = "19:00"
    ASIAN_KILL_ZONE_END: str = "22:00"
    
    # External Data Sources
    NEWS_API_KEY: Optional[str] = Field(default=None, env="NEWS_API_KEY")
    FRED_API_KEY: Optional[str] = Field(default=None, env="FRED_API_KEY")
    ALPHA_VANTAGE_KEY: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_KEY")
    
    # Notifications
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, env="TELEGRAM_CHAT_ID")
    DISCORD_WEBHOOK_URL: Optional[str] = Field(default=None, env="DISCORD_WEBHOOK_URL")
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/golden-ai.log"
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("TIMEFRAMES", pre=True)
    def parse_timeframes(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",")]
        return v


# Singleton instance
settings = Settings()
