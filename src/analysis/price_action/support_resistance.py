"""
الدعم والمقاومة
Support and Resistance Levels
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from scipy.signal import argrelextrema


class SupportResistanceDetector:
    """
    كاشف مستويات الدعم والمقاومة
    """
    
    def __init__(self, lookback: int = 20, min_touches: int = 2):
        self.lookback = lookback
        self.min_touches = min_touches
        
    def detect(self, df: pd.DataFrame) -> Dict:
        """اكتشاف المستويات"""
        
        # اكتشاف القمم والقيعان المحلية
        highs = df['high'].values
        lows = df['low'].values
        
        # استخدام argrelextrema للعثور على النقاط المحلية
        local_max = argrelextrema(highs, np.greater, order=5)[0]
        local_min = argrelextrema(lows, np.less, order=5)[0]
        
        # تجميع المستويات المتقاربة
        resistance_levels = self._cluster_levels(highs[local_max])
        support_levels = self._cluster_levels(lows[local_min])
        
        # التحقق من القوة
        resistance_levels = self._validate_levels(df, resistance_levels, 'high')
        support_levels = self._validate_levels(df, support_levels, 'low')
        
        return {
            'resistance': resistance_levels,
            'support': support_levels,
            'nearest_resistance': self._find_nearest(df['close'].iloc[-1], resistance_levels),
            'nearest_support': self._find_nearest(df['close'].iloc[-1], support_levels),
            'current_position': self._price_position(
                df['close'].iloc[-1], 
                support_levels, 
                resistance_levels
            )
        }
    
    def _cluster_levels(self, levels: np.ndarray, tolerance: float = 0.002) -> List[float]:
        """تجميع المستويات المتقاربة"""
        if len(levels) == 0:
            return []
        
        sorted_levels = np.sort(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if abs(level - np.mean(current_cluster)) / np.mean(current_cluster) <= tolerance:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        
        if current_cluster:
            clusters.append(np.mean(current_cluster))
        
        return clusters
    
    def _validate_levels(
        self, 
        df: pd.DataFrame, 
        levels: List[float], 
        price_type: str
    ) -> List[Dict]:
        """التحقق من قوة المستويات"""
        validated = []
        
        for level in levels:
            touches = self._count_touches(df, level, price_type)
            if touches >= self.min_touches:
                validated.append({
                    'price': round(level, 2),
                    'touches': touches,
                    'strength': min(touches / 5, 1.0),  # تطبيع
                    'distance_percent': abs(df['close'].iloc[-1] - level) / level * 100
                })
        
        return sorted(validated, key=lambda x: x['strength'], reverse=True)
    
    def _count_touches(self, df: pd.DataFrame, level: float, price_type: str) -> int:
        """حساب عدد لمسات المستوى"""
        tolerance = level * 0.001  # 0.1%
        
        if price_type == 'high':
            touches = ((df['high'] >= level - tolerance) & 
                      (df['high'] <= level + tolerance)).sum()
        else:
            touches = ((df['low'] >= level - tolerance) & 
                      (df['low'] <= level + tolerance)).sum()
        
        return int(touches)
    
    def _find_nearest(self, price: float, levels: List[Dict]) -> Dict:
        """إيجاد أقرب مستوى"""
        if not levels:
            return {}
        
        nearest = min(levels, key=lambda x: abs(x['price'] - price))
        return nearest
    
    def _price_position(
        self, 
        price: float, 
        support: List[Dict], 
        resistance: List[Dict]
    ) -> str:
        """تحديد موقع السعر"""
        if not support or not resistance:
            return 'unknown'
        
        support_prices = [s['price'] for s in support]
        resistance_prices = [r['price'] for r in resistance]
        
        nearest_support = max(support_prices) if support_prices else 0
        nearest_resistance = min(resistance_prices) if resistance_prices else float('inf')
        
        if price < nearest_support:
            return 'below_support'
        elif price > nearest_resistance:
            return 'above_resistance'
        else:
            return 'between_levels'
