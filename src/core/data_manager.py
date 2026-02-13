"""
مدير البيانات
Data Manager
"""

import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import asyncio

from src.data.connectors.mt5_connector import mt5_connector
from src.data.storage.timescale_db import TimescaleDB
from src.data.storage.redis_cache import RedisCache


class DataManager:
    """
    مدير موحد للبيانات مع التخزين المؤقت
    """
    
    def __init__(self):
        self.db = TimescaleDB()
        self.cache = RedisCache()
        self.buffer: Dict[str, pd.DataFrame] = {}
        
    async def get_data(
        self,
        symbol: str,
        timeframe: str,
        count: int = 1000,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        جلب البيانات (مع التخزين المؤقت)
        """
        cache_key = f"{symbol}_{timeframe}_{count}"
        
        # محاولة من الكاش
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # محاولة من قاعدة البيانات
        db_data = self.db.get_ohlcv(symbol, timeframe, limit=count)
        if len(db_data) >= count * 0.9:  # 90% من البيانات متوفرة
            if use_cache:
                self.cache.set(cache_key, db_data, ttl=300)
            return db_data
        
        # جلب من MT5
        mt5_data = await mt5_connector.get_rates(symbol, timeframe, count)
        
        # حفظ في قاعدة البيانات
        self.db.save_ohlcv(symbol, timeframe, mt5_data)
        
        # تخزين مؤقت
        if use_cache:
            self.cache.set(cache_key, mt5_data, ttl=300)
        
        return mt5_data
    
    async def get_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        جلب بيانات متعددة الأطر الزمنية
        """
        tasks = [
            self.get_data(symbol, tf, count=500)
            for tf in timeframes
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            tf: data for tf, data in zip(timeframes, results)
        }
    
    def get_latest(self, symbol: str, timeframe: str) -> Optional[pd.Series]:
        """
        جلب آخر شمعة
        """
        key = f"{symbol}_{timeframe}_latest"
        return self.cache.get(key)
    
    def update_latest(self, symbol: str, timeframe: str, data: pd.Series):
        """
        تحديث آخر شمعة
        """
        key = f"{symbol}_{timeframe}_latest"
        self.cache.set(key, data, ttl=60)
