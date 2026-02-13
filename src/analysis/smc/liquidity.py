"""
تحليل السيولة (Liquidity Analysis)
Liquidity sweeps and pools detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class LiquidityPool:
    """تجمع سيولة"""
    price_level: float
    type: str  # "high" or "low"
    strength: float
    swept: bool = False
    sweep_timestamp: pd.Timestamp = None


class LiquidityAnalyzer:
    """
    محلل السيولة مع:
    - اكتشاف تجمعات السيولة (Liquidity Pools)
    - تحديد الـ Liquidity Sweeps
    - تقييم قوة السيولة
    """
    
    def __init__(self, lookback: int = 20, touch_threshold: int = 2):
        self.lookback = lookback
        self.touch_threshold = touch_threshold
        
    def analyze(self, df: pd.DataFrame, swing_points: List[Dict]) -> Dict:
        """
        تحليل السيولة الكامل
        """
        # اكتشاف مستويات السيولة
        liquidity_levels = self._find_liquidity_levels(df, swing_points)
        
        # التحقق من الـ Sweeps
        swept_highs, swept_lows = self._detect_sweeps(df, liquidity_levels)
        
        # تحديث حالة المستويات
        for level in liquidity_levels:
            if level.type == "high" and level.price_level in swept_highs:
                level.swept = True
                level.sweep_timestamp = df.index[-1]
            elif level.type == "low" and level.price_level in swept_lows:
                level.swept = True
                level.sweep_timestamp = df.index[-1]
        
        return {
            'levels': [self._level_to_dict(l) for l in liquidity_levels],
            'swept_highs': len(swept_highs),
            'swept_lows': len(swept_lows),
            'strongest_level': self._find_strongest_level(liquidity_levels),
            'recent_sweep': len(swept_highs) > 0 or len(swept_lows) > 0
        }
    
    def _find_liquidity_levels(
        self,
        df: pd.DataFrame,
        swing_points: List[Dict]
    ) -> List[LiquidityPool]:
        """اكتشاف مستويات السيولة"""
        levels = []
        
        # استخدام نقاط الأرجوحة كمستويات أساسية
        for sp in swing_points[-self.lookback:]:
            # حساب عدد اللمسات
            touches = self._count_touches(df, sp['price'])
            
            if touches >= self.touch_threshold:
                strength = self._calculate_strength(df, sp['price'], touches)
                pool = LiquidityPool(
                    price_level=sp['price'],
                    type=sp['type'],
                    strength=strength
                )
                levels.append(pool)
        
        # إضافة مستويات Equal Highs/Lows
        equal_levels = self._find_equal_levels(df)
        levels.extend(equal_levels)
        
        # ترتيب حسب القوة
        levels.sort(key=lambda x: x.strength, reverse=True)
        
        return levels
    
    def _count_touches(self, df: pd.DataFrame, level: float, tolerance: float = 0.001) -> int:
        """حساب عدد لمسات المستوى"""
        touches = 0
        
        for _, row in df.iterrows():
            if abs(row['high'] - level) <= level * tolerance or \
               abs(row['low'] - level) <= level * tolerance:
                touches += 1
        
        return touches
    
    def _calculate_strength(
        self,
        df: pd.DataFrame,
        level: float,
        touches: int
    ) -> float:
        """حساب قوة مستوى السيولة"""
        # العوامل المؤثرة:
        # 1. عدد اللمسات (أكثر = أقوى)
        # 2. القرب من السعر الحالي (أقرب = أقوى)
        # 3. الحجم عند اللمسات
        
        touch_factor = min(touches / 5, 1.0)  # تطبيع
        
        current_price = df['close'].iloc[-1]
        distance = abs(current_price - level) / current_price
        proximity_factor = max(0, 1 - distance * 100)  # كلما كان أقرب، أقوى
        
        # يمكن إضافة عامل الحجم هنا
        
        return (touch_factor * 0.6 + proximity_factor * 0.4)
    
    def _find_equal_levels(self, df: pd.DataFrame) -> List[LiquidityPool]:
        """البحث عن مستويات متساوية (Equal Highs/Lows)"""
        pools = []
        tolerance = 0.0005  # 0.05% للذهب
        
        # البحث عن قمم متساوية
        highs = df['high'].values
        for i in range(len(highs)):
            for j in range(i+1, min(i+20, len(highs))):
                if abs(highs[i] - highs[j]) <= highs[i] * tolerance:
                    strength = 0.7  # قوة جيدة لـ Equal Highs
                    pools.append(LiquidityPool(
                        price_level=highs[i],
                        type='high',
                        strength=strength
                    ))
        
        # البحث عن قيعان متساوية
        lows = df['low'].values
        for i in range(len(lows)):
            for j in range(i+1, min(i+20, len(lows))):
                if abs(lows[i] - lows[j]) <= lows[i] * tolerance:
                    strength = 0.7
                    pools.append(LiquidityPool(
                        price_level=lows[i],
                        type='low',
                        strength=strength
                    ))
        
        return pools
    
    def _detect_sweeps(
        self,
        df: pd.DataFrame,
        levels: List[LiquidityPool]
    ) -> tuple:
        """اكتشاف الـ Liquidity Sweeps"""
        swept_highs = []
        swept_lows = []
        
        if len(df) < 3:
            return swept_highs, swept_lows
        
        # آخر 3 شمعات للتحقق
        recent = df.iloc[-3:]
        
        for level in levels:
            if level.type == 'high':
                # Sweep: اختراق القمة ثم العودة
                if any(recent['high'] > level.price_level) and \
                   recent['close'].iloc[-1] < level.price_level:
                    swept_highs.append(level.price_level)
                    
            elif level.type == 'low':
                # Sweep: اختراق القاع ثم العودة
                if any(recent['low'] < level.price_level) and \
                   recent['close'].iloc[-1] > level.price_level:
                    swept_lows.append(level.price_level)
        
        return swept_highs, swept_lows
    
    def _find_strongest_level(self, levels: List[LiquidityPool]) -> Optional[Dict]:
        """العثور على أقوى مستوى"""
        if not levels:
            return None
        
        strongest = max(levels, key=lambda x: x.strength)
        return self._level_to_dict(strongest)
    
    def _level_to_dict(self, level: LiquidityPool) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'price': level.price_level,
            'type': level.type,
            'strength': level.strength,
            'swept': level.swept,
            'sweep_time': level.sweep_timestamp.isoformat() if level.sweep_timestamp else None
        }
