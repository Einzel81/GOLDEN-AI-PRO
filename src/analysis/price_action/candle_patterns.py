"""
أنماط الشموع اليابانية
Japanese Candlestick Patterns Recognition
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class CandlePatternRecognizer:
    """
    متعرف على أنماط الشموع مع:
    - الأنماط الانعكاسية
    - الأنماط الاستمرارية
    - قياس قوة النمط
    """
    
    def __init__(self):
        self.patterns = {
            'reversal': [],
            'continuation': []
        }
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل أنماط الشموع
        """
        if len(df) < 5:
            return {'patterns': [], 'strength': 0}
        
        patterns = []
        
        # الأنماط الانعكاسية
        if self._is_hammer(df):
            patterns.append({
                'name': 'Hammer',
                'type': 'reversal',
                'direction': 'bullish',
                'strength': self._hammer_strength(df),
                'position': 'bottom'
            })
        
        if self._is_shooting_star(df):
            patterns.append({
                'name': 'Shooting Star',
                'type': 'reversal',
                'direction': 'bearish',
                'strength': self._shooting_star_strength(df),
                'position': 'top'
            })
        
        if self._is_engulfing_bullish(df):
            patterns.append({
                'name': 'Bullish Engulfing',
                'type': 'reversal',
                'direction': 'bullish',
                'strength': 0.8,
                'position': 'bottom'
            })
        
        if self._is_engulfing_bearish(df):
            patterns.append({
                'name': 'Bearish Engulfing',
                'type': 'reversal',
                'direction': 'bearish',
                'strength': 0.8,
                'position': 'top'
            })
        
        if self._is_morning_star(df):
            patterns.append({
                'name': 'Morning Star',
                'type': 'reversal',
                'direction': 'bullish',
                'strength': 0.9,
                'position': 'bottom'
            })
        
        if self._is_evening_star(df):
            patterns.append({
                'name': 'Evening Star',
                'type': 'reversal',
                'direction': 'bearish',
                'strength': 0.9,
                'position': 'top'
            })
        
        if self._is_doji(df):
            patterns.append({
                'name': 'Doji',
                'type': 'indecision',
                'direction': 'neutral',
                'strength': 0.5,
                'position': 'any'
            })
        
        # حساب القوة الإجمالية
        total_strength = self._calculate_overall_strength(patterns, df)
        
        return {
            'patterns': patterns,
            'count': len(patterns),
            'dominant_direction': self._get_dominant_direction(patterns),
            'strength': total_strength,
            'last_candle': self._analyze_last_candle(df)
        }
    
    def _is_hammer(self, df: pd.DataFrame) -> bool:
        """التحقق من نمط المطرقة"""
        if len(df) < 1:
            return False
        
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        
        # الجسم صغير، الظل السفلي طويل، الظل العلوي قصير
        return (body > 0 and 
                lower_shadow > body * 2 and 
                upper_shadow < body * 0.5)
    
    def _is_shooting_star(self, df: pd.DataFrame) -> bool:
        """التحقق من نمط النيزك"""
        if len(df) < 1:
            return False
        
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        
        return (body > 0 and 
                upper_shadow > body * 2 and 
                lower_shadow < body * 0.5)
    
    def _is_engulfing_bullish(self, df: pd.DataFrame) -> bool:
        """التحقق من الابتلاع الصاعد"""
        if len(df) < 2:
            return False
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # الشمعة السابقة هابطة، الحالية صاعدة وتبتلعها
        return (prev['close'] < prev['open'] and  # هابطة
                curr['close'] > curr['open'] and   # صاعدة
                curr['open'] < prev['close'] and   # تبتلع
                curr['close'] > prev['open'])
    
    def _is_engulfing_bearish(self, df: pd.DataFrame) -> bool:
        """التحقق من الابتلاع الهابط"""
        if len(df) < 2:
            return False
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        return (prev['close'] > prev['open'] and  # صاعدة
                curr['close'] < curr['open'] and   # هابطة
                curr['open'] > prev['close'] and   # تبتلع
                curr['close'] < prev['open'])
    
    def _is_morning_star(self, df: pd.DataFrame) -> bool:
        """التحقق من نجمة الصباح"""
        if len(df) < 3:
            return False
        
        first = df.iloc[-3]
        second = df.iloc[-2]
        third = df.iloc[-1]
        
        # شمعة هابطة كبيرة، ثم دوجي، ثم صاعدة
        return (first['close'] < first['open'] and  # هابطة
                abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3 and  # دوجي
                third['close'] > third['open'] and   # صاعدة
                third['close'] > (first['open'] + first['close']) / 2)  # تغلق فوق منتصف الأولى
    
    def _is_evening_star(self, df: pd.DataFrame) -> bool:
        """التحقق من نجمة المساء"""
        if len(df) < 3:
            return False
        
        first = df.iloc[-3]
        second = df.iloc[-2]
        third = df.iloc[-1]
        
        return (first['close'] > first['open'] and  # صاعدة
                abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3 and
                third['close'] < third['open'] and   # هابطة
                third['close'] < (first['open'] + first['close']) / 2)
    
    def _is_doji(self, df: pd.DataFrame) -> bool:
        """التحقق من الدوجي"""
        if len(df) < 1:
            return False
        
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        range_candle = candle['high'] - candle['low']
        
        return body < range_candle * 0.1  # الجسم أقل من 10% من المدى
    
    def _hammer_strength(self, df: pd.DataFrame) -> float:
        """حساب قوة المطرقة"""
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        
        ratio = lower_shadow / body if body > 0 else 0
        return min(ratio / 3, 1.0)  # تطبيع
    
    def _shooting_star_strength(self, df: pd.DataFrame) -> float:
        """حساب قوة النيزك"""
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        
        ratio = upper_shadow / body if body > 0 else 0
        return min(ratio / 3, 1.0)
    
    def _calculate_overall_strength(self, patterns: List[Dict], df: pd.DataFrame) -> float:
        """حساب القوة الإجمالية للأنماط"""
        if not patterns:
            return 0.0
        
        avg_strength = np.mean([p['strength'] for p in patterns])
        
        # تعزيز القوة إذا تطابق الاتجاه مع الاتجاه العام
        trend = self._detect_trend(df)
        bullish_count = sum(1 for p in patterns if p['direction'] == 'bullish')
        bearish_count = sum(1 for p in patterns if p['direction'] == 'bearish')
        
        if trend == 'bullish' and bullish_count > bearish_count:
            avg_strength *= 1.2
        elif trend == 'bearish' and bearish_count > bullish_count:
            avg_strength *= 1.2
        
        return min(avg_strength, 1.0)
    
    def _detect_trend(self, df: pd.DataFrame, period: int = 20) -> str:
        """اكتشاف الاتجاه العام"""
        if len(df) < period:
            return 'neutral'
        
        sma = df['close'].rolling(window=period).mean().iloc[-1]
        current = df['close'].iloc[-1]
        
        if current > sma * 1.02:
            return 'bullish'
        elif current < sma * 0.98:
            return 'bearish'
        return 'neutral'
    
    def _get_dominant_direction(self, patterns: List[Dict]) -> str:
        """تحديد الاتجاه السائد"""
        if not patterns:
            return 'neutral'
        
        bullish = sum(1 for p in patterns if p['direction'] == 'bullish')
        bearish = sum(1 for p in patterns if p['direction'] == 'bearish')
        
        if bullish > bearish:
            return 'bullish'
        elif bearish > bullish:
            return 'bearish'
        return 'neutral'
    
    def _analyze_last_candle(self, df: pd.DataFrame) -> Dict:
        """تحليل آخر شمعة"""
        if len(df) < 1:
            return {}
        
        candle = df.iloc[-1]
        body = candle['close'] - candle['open']
        range_candle = candle['high'] - candle['low']
        
        return {
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close'],
            'body_size': abs(body),
            'range': range_candle,
            'body_to_range_ratio': abs(body) / range_candle if range_candle > 0 else 0,
            'direction': 'bullish' if body > 0 else 'bearish' if body < 0 else 'doji'
        }
