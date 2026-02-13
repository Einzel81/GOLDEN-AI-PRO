"""
اكتشاف فجوات القيمة العادلة (Fair Value Gaps)
FVG Detection with nested and overlapping gap handling
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class FairValueGap:
    """فجوة قيمة عادلة"""
    start_index: int
    end_index: int
    top: float
    bottom: float
    type: str  # "bullish" or "bearish"
    size: float
    filled: bool = False


class FVGDetector:
    """
    كاشف FVG مع:
    - اكتشاف Bullish/Bearish FVGs
    - تتبع الحالة (Filled/Unfilled)
    - تصفية حسب الحجم
    """
    
    def __init__(self, min_gap_size: float = 0.5):
        """
        min_gap_size: الحد الأدنى لحجم الفجوة بالنقاط (لـ XAUUSD)
        """
        self.min_gap_size = min_gap_size
        
    def detect(self, df: pd.DataFrame) -> List[Dict]:
        """
        اكتشاف جميع FVGs
        """
        fvgs = []
        
        for i in range(1, len(df) - 1):
            prev_candle = df.iloc[i-1]
            curr_candle = df.iloc[i]
            next_candle = df.iloc[i+1]
            
            # Bullish FVG: الفجوة بين high الشمعة السابقة و low الشمعة التالية
            if prev_candle['high'] < next_candle['low']:
                gap_size = next_candle['low'] - prev_candle['high']
                
                if gap_size >= self.min_gap_size:
                    fvg = FairValueGap(
                        start_index=i-1,
                        end_index=i+1,
                        top=next_candle['low'],
                        bottom=prev_candle['high'],
                        type='bullish',
                        size=gap_size
                    )
                    fvgs.append(fvg)
            
            # Bearish FVG: الفجوة بين low الشمعة السابقة و high الشمعة التالية
            elif prev_candle['low'] > next_candle['high']:
                gap_size = prev_candle['low'] - next_candle['high']
                
                if gap_size >= self.min_gap_size:
                    fvg = FairValueGap(
                        start_index=i-1,
                        end_index=i+1,
                        top=prev_candle['low'],
                        bottom=next_candle['high'],
                        type='bearish',
                        size=gap_size
                    )
                    fvgs.append(fvg)
        
        # تتبع حالة الفجوات (Filled/Unfilled)
        fvgs = self._track_filling(df, fvgs)
        
        # تحويل إلى قوائم
        return [self._fvg_to_dict(fvg, df) for fvg in fvgs]
    
    def _track_filling(
        self,
        df: pd.DataFrame,
        fvgs: List[FairValueGap]
    ) -> List[FairValueGap]:
        """تتبع ما إذا تم ملء الفجوات"""
        for fvg in fvgs:
            for i in range(fvg.end_index + 1, len(df)):
                candle = df.iloc[i]
                
                # التحقق من ملء الفجوة
                if fvg.type == 'bullish':
                    # Bullish FVG تم ملؤها إذا وصل السعر إلى أسفل الفجوة
                    if candle['low'] <= fvg.bottom:
                        fvg.filled = True
                        break
                else:
                    # Bearish FVG تم ملؤها إذا وصل السعر إلى أعلى الفجوة
                    if candle['high'] >= fvg.top:
                        fvg.filled = True
                        break
        
        return fvgs
    
    def _fvg_to_dict(self, fvg: FairValueGap, df: pd.DataFrame) -> Dict:
        """تحويل FVG إلى قاموس"""
        return {
            'start_index': fvg.start_index,
            'end_index': fvg.end_index,
            'top': fvg.top,
            'bottom': fvg.bottom,
            'type': fvg.type,
            'size': fvg.size,
            'filled': fvg.filled,
            'start_time': df.index[fvg.start_index].isoformat(),
            'end_time': df.index[fvg.end_index].isoformat(),
            'fresh': not fvg.filled  # FVG جديدة = فرصة تداول
        }
