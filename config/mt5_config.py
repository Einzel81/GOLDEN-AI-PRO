"""
إعدادات MetaTrader 5
MetaTrader 5 Configuration
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class MT5SymbolConfig:
    """إعدادات الرمز"""
    name: str
    digits: int
    point: float
    spread_avg: float
    trade_stops_level: int
    volume_min: float
    volume_max: float
    volume_step: float


@dataclass
class MT5ServerConfig:
    """إعدادات الخادم"""
    host: str = "127.0.0.1"
    zmq_port: int = 15555
    timeout_ms: int = 5000
    reconnect_attempts: int = 3
    reconnect_delay_sec: int = 5


# إعدادات الرموز المدعومة
SYMBOLS_CONFIG: Dict[str, MT5SymbolConfig] = {
    "XAUUSD": MT5SymbolConfig(
        name="XAUUSD",
        digits=2,
        point=0.01,
        spread_avg=20.0,
        trade_stops_level=100,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01
    ),
    "EURUSD": MT5SymbolConfig(
        name="EURUSD",
        digits=5,
        point=0.00001,
        spread_avg=1.0,
        trade_stops_level=10,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01
    ),
    "GBPUSD": MT5SymbolConfig(
        name="GBPUSD",
        digits=5,
        point=0.00001,
        spread_avg=1.5,
        trade_stops_level=10,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01
    )
}

# إعدادات الأطر الزمنية
TIMEFRAMES: Dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
    "MN1": 43200
}

# إعدادات الاتصال الافتراضية
DEFAULT_SERVER_CONFIG = MT5ServerConfig()

# إعدادات التداول
TRADING_CONFIG = {
    "max_slippage_points": 3,
    "max_spread_points": 50,
    "order_retry_attempts": 3,
    "order_retry_delay_ms": 500,
    "use_market_execution": True,
    "partial_fill_accepted": False
}
