"""
تحليل بنية السوق (BOS/CHoCH)
Market Structure Analysis - Break of Structure & Change of Character
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class StructureType(Enum):
    BOS = "break_of_structure"
    CHOCH = "change_of_character"


@dataclass
class SwingPoint:
    """نقطة أرجوحة"""
    index: int
    price: float
    type: str  # "high" or "low"
    timestamp: pd.Timestamp


class MarketStructureAnalyzer:
    """
    محلل بنية السوق لاكتشاف:
    - Break of Structure (BOS)
    - Change of Character (CHoCH)
    - Market Structure Shift (MSS)
    """
    
    def __init__(self, swing_lookback: int = 5):
        self.swing_lookback = swing_lookback
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل بنية السوق الكامل
        """
        # 1. اكتشاف نقاط الأرجوحة
        swing_points = self._find_swing_points(df)
        
        # 2. تحديد الاتجاه
        trend = self._determine_trend(swing_points)
        
        # 3. اكتشاف BOS و CHoCH
        bos_list = self._detect_bos(df, swing_points, trend)
        choch_list = self._detect_choch(df, swing_points, trend)
        
        # 4. اكتشاف MSS
        mss = self._detect_mss(df, swing_points, trend)
        
        return {
            'trend': trend,
            'swing_points': [self._swing_to_dict(sp) for sp in swing_points],
            'bos': bos_list,
            'choch': choch_list,
            'mss': mss,
            'structure_strength': self._calculate_structure_strength(bos_list, choch_list)
        }
    
    def _find_swing_points(self, df: pd.DataFrame) -> List[SwingPoint]:
        """اكتشاف نقاط الأرجوحة"""
        swing_points = []
        
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            # Swing High
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, self.swing_lookback+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, self.swing_lookback+1)):
                swing_points.append(SwingPoint(
                    index=i,
                    price=df['high'].iloc[i],
                    type='high',
                    timestamp=df.index[i]
                ))
            
            # Swing Low
            elif all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, self.swing_lookback+1)) and \
                 all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, self.swing_lookback+1)):
                swing_points.append(SwingPoint(
                    index=i,
                    price=df['low'].iloc[i],
                    type='low',
                    timestamp=df.index[i]
                ))
        
        return swing_points
    
    def _determine_trend(self, swing_points: List[SwingPoint]) -> str:
        """تحديد الاتجاه العام"""
        if len(swing_points) < 4:
            return "neutral"
        
        # تحليل آخر 4 نقاط أرجوحة
        recent = swing_points[-4:]
        
        higher_highs = recent[-1].price > recent[-3].price if recent[-1].type == 'high' else recent[-2].price > recent[-4].price
        higher_lows = recent[-1].price > recent[-3].price if recent[-1].type == 'low' else recent[-2].price > recent[-4].price
        
        if higher_highs and higher_lows:
            return "bullish"
        elif not higher_highs and not higher_lows:
            return "bearish"
        else:
            return "neutral"
    
    def _detect_bos(self, df: pd.DataFrame, swing_points: List[SwingPoint], trend: str) -> List[Dict]:
        """اكتشاف Break of Structure"""
        bos_list = []
        
        if len(swing_points) < 2:
            return bos_list
        
        for i in range(1, len(swing_points)):
            prev = swing_points[i-1]
            curr = swing_points[i]
            
            # BOS Bullish: كسر قمة سابقة
            if trend == "bullish" and prev.type == 'high' and curr.type == 'high':
                if curr.price > prev.price:
                    bos_list.append({
                        'type': 'bullish_bos',
                        'index': curr.index,
                        'price': curr.price,
                        'broken_level': prev.price,
                        'timestamp': curr.timestamp
                    })
            
            # BOS Bearish: كسر قاع سابق
            elif trend == "bearish" and prev.type == 'low' and curr.type == 'low':
                if curr.price < prev.price:
                    bos_list.append({
                        'type': 'bearish_bos',
                        'index': curr.index,
                        'price': curr.price,
                        'broken_level': prev.price,
                        'timestamp': curr.timestamp
                    })
        
        return bos_list
    
    def _detect_choch(self, df: pd.DataFrame, swing_points: List[SwingPoint], trend: str) -> List[Dict]:
        """اكتشاف Change of Character"""
        choch_list = []
        
        if len(swing_points) < 3:
            return choch_list
        
        for i in range(2, len(swing_points)):
            # CHoCH Bullish: قاع أعلى من القاع السابق في اتجاه هابط
            if trend == "bearish":
                lows = [sp for sp in swing_points[max(0, i-3):i+1] if sp.type == 'low']
                if len(lows) >= 2 and lows[-1].price > lows[-2].price:
                    choch_list.append({
                        'type': 'bullish_choch',
                        'index': lows[-1].index,
                        'price': lows[-1].price,
                        'previous_low': lows[-2].price,
                        'timestamp': lows[-1].timestamp
                    })
            
            # CHoCH Bearish: قمة أقل من القمة السابقة في اتجاه صاعد
            elif trend == "bullish":
                highs = [sp for sp in swing_points[max(0, i-3):i+1] if sp.type == 'high']
                if len(highs) >= 2 and highs[-1].price < highs[-2].price:
                    choch_list.append({
                        'type': 'bearish_choch',
                        'index': highs[-1].index,
                        'price': highs[-1].price,
                        'previous_high': highs[-2].price,
                        'timestamp': highs[-1].timestamp
                    })
        
        return choch_list
    
    def _detect_mss(self, df: pd.DataFrame, swing_points: List[SwingPoint], trend: str) -> List[Dict]:
        """اكتشاف Market Structure Shift"""
        mss_list = []
        
        if len(swing_points) < 4:
            return mss_list
        
        # MSS يحدث عندما يتغير الاتجاه مع كسر قمة/قاع مهم
        recent = swing_points[-4:]
        
        # MSS Bullish: كسر قمة مع تغير الاتجاه
        if trend == "bullish":
            highs = [sp for sp in recent if sp.type == 'high']
            if len(highs) >= 2 and highs[-1].price > highs[0].price:
                mss_list.append({
                    'type': 'bullish_mss',
                    'index': highs[-1].index,
                    'price': highs[-1].price,
                    'timestamp': highs[-1].timestamp
                })
        
        # MSS Bearish: كسر قاع مع تغير الاتجاه
        elif trend == "bearish":
            lows = [sp for sp in recent if sp.type == 'low']
            if len(lows) >= 2 and lows[-1].price < lows[0].price:
                mss_list.append({
                    'type': 'bearish_mss',
                    'index': lows[-1].index,
                    'price': lows[-1].price,
                    'timestamp': lows[-1].timestamp
                })
        
        return mss_list
    
    def _calculate_structure_strength(self, bos: List[Dict], choch: List[Dict]) -> float:
        """حساب قوة البنية"""
        score = 0.0
        
        # BOS قوي
        score += len(bos) * 0.15
        
        # CHoCH أقوى
        score += len(cho
