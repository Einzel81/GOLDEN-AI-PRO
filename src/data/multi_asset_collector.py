"""
جامع بيانات متعدد الأصول للتحليل المشترك
يدمج DXY، الفضة، والمعادن الأخرى مع الذهب
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging
import sys
if sys.platform == 'win32':
    from MetaTrader5 import *
else:
    from .mt5_mock import *
    print("⚠️  Running in Linux Mode - Using Mock MT5")

logger = logging.getLogger(__name__)


class MultiAssetDataCollector:
    """
    جامع بيانات متعدد الأصول للتحليل المشترك
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.symbols = {
            'gold': self.config.get('GOLD_SYMBOL', 'XAUUSD'),
            'silver': self.config.get('SILVER_SYMBOL', 'XAGUSD'),
            'dollar_index': self.config.get('DXY_SYMBOL', 'DX1'),
            'platinum': self.config.get('PLATINUM_SYMBOL', 'XPTUSD'),
            'palladium': self.config.get('PALLADIUM_SYMBOL', 'XPDUSD'),
            'copper': self.config.get('COPPER_SYMBOL', 'XCUUSD')
        }
        self.timeframe = self.config.get('TIMEFRAME', 'H1')
        self.lookback_bars = self.config.get('LOOKBACK_BARS', 1000)
        
    def initialize_mt5(self) -> bool:
        """التهيئة والاتصال بـ MT5"""
        if not initialize():
            logger.error("فشل الاتصال بـ MT5")
            return False
        logger.info("تم الاتصال بـ MT5 بنجاح")
        return True
    
    def shutdown(self):
        """إغلاق الاتصال"""
        shutdown()
    
    def fetch_ohlc(self, symbol: str, timeframe: str = None, 
                   bars: int = None) -> Optional[pd.DataFrame]:
        """
        جلب بيانات OHLC لرمز محدد
        """
        tf = self._get_timeframe(timeframe or self.timeframe)
        n_bars = bars or self.lookback_bars
        
        try:
            rates = copy_rates_from_pos(symbol, tf, 0, n_bars)
            if rates is None or len(rates) == 0:
                logger.warning(f"لا توجد بيانات لـ {symbol}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df['symbol'] = symbol
            
            return df
            
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات {symbol}: {e}")
            return None
    
    def fetch_all_assets(self) -> Dict[str, pd.DataFrame]:
        """
        جلب بيانات جميع الأصول المتاحة
        """
        data = {}
        
        for name, symbol in self.symbols.items():
            df = self.fetch_ohlc(symbol)
            if df is not None:
                data[name] = df
                logger.info(f"تم جلب {len(df)} شمعة لـ {name} ({symbol})")
            else:
                logger.warning(f"تخطي {name} - غير متوفر")
        
        return data
    
    def get_correlation_matrix(self, data: Dict[str, pd.DataFrame], 
                               window: int = 20) -> pd.DataFrame:
        """
        حساب مصفوفة الارتباط بين الأصول
        """
        # إنشاء DataFrame موحد للأسعار الإغلاق
        prices = pd.DataFrame()
        
        for name, df in data.items():
            if df is not None and not df.empty:
                prices[name] = df['close']
        
        if prices.empty:
            return pd.DataFrame()
        
        # حساب الارتباط المتحرك
        correlation = prices.pct_change().rolling(window=window).corr()
        
        return correlation
    
    def get_dxy_data(self) -> Optional[pd.DataFrame]:
        """جلب بيانات مؤشر الدولار"""
        return self.fetch_ohlc(self.symbols['dollar_index'])
    
    def get_silver_data(self) -> Optional[pd.DataFrame]:
        """جلب بيانات الفضة"""
        return self.fetch_ohlc(self.symbols['silver'])
    
    def calculate_gold_silver_ratio(self, gold_df: pd.DataFrame, 
                                    silver_df: pd.DataFrame) -> pd.Series:
        """
        حساب نسبة الذهب/الفضة (مؤشر تاريخي مهم)
        """
        # محاذاة البيانات
        aligned_gold, aligned_silver = gold_df.align(silver_df, join='inner')
        
        ratio = aligned_gold['close'] / aligned_silver['close']
        return ratio
    
    def _get_timeframe(self, tf: str):
        """تحويل نص الإطار الزمني إلى ثابت MT5"""
        timeframes = {
            'M1': TIMEFRAME_M1,
            'M5': TIMEFRAME_M5,
            'M15': TIMEFRAME_M15,
            'M30': TIMEFRAME_M30,
            'H1': TIMEFRAME_H1,
            'H4': TIMEFRAME_H4,
            'D1': TIMEFRAME_D1,
            'W1': TIMEFRAME_W1,
        }
        return timeframes.get(tf, TIMEFRAME_H1)


# ============================================================
# دوال مساعدة للاستخدام السريع
# ============================================================

def fetch_market_context(config: Dict = None) -> Dict:
    """
    دالة سريعة لجلب السياق السوقي الكامل
    """
    collector = MultiAssetDataCollector(config)
    
    if not collector.initialize_mt5():
        return {}
    
    try:
        data = collector.fetch_all_assets()
        
        # حساب الارتباطات
        if len(data) >= 2:
            corr_matrix = collector.get_correlation_matrix(data)
        else:
            corr_matrix = pd.DataFrame()
        
        # حساب نسبة الذهب/الفضة
        gold_silver_ratio = None
        if 'gold' in data and 'silver' in data:
            gold_silver_ratio = collector.calculate_gold_silver_ratio(
                data['gold'], data['silver']
            )
        
        return {
            'data': data,
            'correlation_matrix': corr_matrix,
            'gold_silver_ratio': gold_silver_ratio,
            'timestamp': datetime.now()
        }
        
    finally:
        collector.shutdown()
