"""
تحليل الاتجاه
Trend Analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List


class TrendAnalyzer:
    """
    محلل الاتجاه متعدد الأطر
    """
    
    def __init__(self):
        self.trend_periods = [10, 20, 50, 200]
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """تحليل الاتجاه"""
        
        trends = {}
        
        for period in self.trend_periods:
            trend = self._calculate_trend(df, period)
            trends[f'sma_{period}'] = trend
        
        # الاتجاه العام
        overall_trend = self._determine_overall_trend(trends)
        
        # قوة الاتجاه
        trend_strength = self._calculate_trend_strength(df)
        
        # الاتجاه على مستويات مختلفة
        multi_timeframe = self._multi_timeframe_alignment(df)
        
        return {
            'overall': overall_trend,
            'strength': trend_strength,
            'multi_timeframe': multi_timeframe,
            'details': trends,
            'adx': self._calculate_adx(df),
            'trend_lines': self._find_trend_lines(df)
        }
    
    def _calculate_trend(self, df: pd.DataFrame, period: int) -> str:
        """حساب الاتجاه بناءً على SMA"""
        if len(df) < period:
            return 'neutral'
        
        sma = df['close'].rolling(window=period).mean().iloc[-1]
        current = df['close'].iloc[-1]
        prev = df['close'].iloc[-period]
        
        if current > sma and current > prev:
            return 'bullish'
        elif current < sma and current < prev:
            return 'bearish'
        return 'neutral'
    
    def _determine_overall_trend(self, trends: Dict) -> str:
        """تحديد الاتجاه العام"""
        values = list(trends.values())
        bullish = values.count('bullish')
        bearish = values.count('bearish')
        
        if bullish > bearish and bullish >= 3:
            return 'strong_bullish'
        elif bearish > bullish and bearish >= 3:
            return 'strong_bearish'
        elif bullish > bearish:
            return 'bullish'
        elif bearish > bullish:
            return 'bearish'
        return 'neutral'
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """حساب قوة الاتجاه (0-1)"""
        if len(df) < 20:
            return 0.0
        
        # حساب زاوية الاتجاه
        x = np.arange(20)
        y = df['close'].iloc[-20:].values
        
        slope, _, r_value, _, _ = np.polyfit(x, y, 1, full=True)
        
        # R-squared كمقياس للقوة
        return min(abs(r_value[0]) if len(r_value) > 0 else 0, 1.0)
    
    def _multi_timeframe_alignment(self, df: pd.DataFrame) -> Dict:
        """محاذاة الأطر الزمنية"""
        short = self._calculate_trend(df, 10)
        medium = self._calculate_trend(df, 20)
        long = self._calculate_trend(df, 50)
        
        aligned = short == medium == long
        
        return {
            'short': short,
            'medium': medium,
            'long': long,
            'aligned': aligned,
            'alignment_score': sum([
                1 if short == medium else 0,
                1 if medium == long else 0,
                1 if short == long else 0
            ]) / 3
        }
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """حساب مؤشر ADX"""
        if len(df) < period + 1:
            return 0.0
        
        # True Range
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # +DM و -DM
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # المتوسطات المتحركة
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=period).mean() / atr
        
        # DX و ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx.iloc[-1] if not np.isnan(adx.iloc[-1]) else 0.0
    
    def _find_trend_lines(self, df: pd.DataFrame) -> Dict:
        """إيجاد خطوط الاتجاه"""
        if len(df) < 20:
            return {}
        
        # خط الاتجاه الصاعد (من القيعان)
        lows = df['low'].iloc[-20:].values
        x = np.arange(len(lows))
        
        # انحدار خطي للقيعان
        slope_up, intercept_up = np.polyfit(x, lows, 1)
        
        # خط الاتجاه الهابط (من القمم)
        highs = df['high'].iloc[-20:].values
        slope_down, intercept_down = np.polyfit(x, highs, 1)
        
        return {
            'uptrend_slope': slope_up,
            'uptrend_angle': np.degrees(np.arctan(slope_up)),
            'downtrend_slope': slope_down,
            'downtrend_angle': np.degrees(np.arctan(slope_down))
        }
