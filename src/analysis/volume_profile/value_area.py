"""
تحليل منطقة القيمة (Value Area)
Value Area Analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


class ValueAreaAnalyzer:
    """
    محلل Value Area (VAH/VAL)
    """
    
    def __init__(self, value_area_percent: float = 0.70):
        self.va_percent = value_area_percent
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل Value Area
        """
        if len(df) < 20:
            return self._empty_result()
        
        # حساب Volume Profile
        vah, val, poc = self._calculate_value_area(df)
        
        current_price = df['close'].iloc[-1]
        
        # تحديد موقع السعر
        if current_price > vah:
            position = 'above_value_area'
        elif current_price < val:
            position = 'below_value_area'
        else:
            position = 'inside_value_area'
        
        # حساب عرض Value Area
        va_width = ((vah - val) / poc) * 100 if poc > 0 else 0
        
        return {
            'vah': round(vah, 2),
            'val': round(val, 2),
            'poc': round(poc, 2),
            'width_percent': round(va_width, 2),
            'current_price': round(current_price, 2),
            'position': position,
            'distance_to_vah': round(vah - current_price, 2) if current_price < vah else 0,
            'distance_to_val': round(current_price - val, 2) if current_price > val else 0,
            'volume_profile_quality': self._assess_quality(df, vah, val)
        }
    
    def _calculate_value_area(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """حساب Value Area"""
        # إنشاء bins للأسعار
        n_bins = 24
        price_bins = np.linspace(df['low'].min(), df['high'].max(), n_bins)
        
        # حساب الحجم لكل bin
        volumes = []
        poc_idx = 0
        max_volume = 0
        
        for i in range(len(price_bins) - 1):
            mask = (df['low'] <= price_bins[i+1]) & (df['high'] >= price_bins[i])
            vol = df[mask]['volume'].sum()
            volumes.append(vol)
            
            if vol > max_volume:
                max_volume = vol
                poc_idx = i
        
        poc = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2
        
        # تجميع الحجم حتى الوصول إلى النسبة المطلوبة
        total_volume = sum(volumes)
        target_volume = total_volume * self.va_percent
        
        # البدء من POC والتوسع
        current_volume = volumes[poc_idx]
        vah_idx = poc_idx
        val_idx = poc_idx
        
        while current_volume < target_volume and (vah_idx < len(volumes) - 1 or val_idx > 0):
            # إضافة الحجم من الأعلى
            if vah_idx < len(volumes) - 1:
                vah_idx += 1
                current_volume += volumes[vah_idx]
            
            # إضافة الحجم من الأسفل
            if val_idx > 0 and current_volume < target_volume:
                val_idx -= 1
                current_volume += volumes[val_idx]
        
        vah = price_bins[vah_idx + 1]
        val = price_bins[val_idx]
        
        return vah, val, poc
    
    def _assess_quality(self, df: pd.DataFrame, vah: float, val: float) -> str:
        """تقييم جودة Volume Profile"""
        va_range = vah - val
        
        if va_range / df['close'].iloc[-1] < 0.01:
            return 'narrow'  # ضيق - قد يشير إلى اختراق وشيك
        elif va_range / df['close'].iloc[-1] > 0.05:
            return 'wide'    # واسع - توازن في السوق
        return 'normal'
    
    def _empty_result(self) -> Dict:
        """نتيجة فارغة"""
        return {
            'vah': 0,
            'val': 0,
            'poc': 0,
            'width_percent': 0,
            'position': 'unknown',
            'volume_profile_quality': 'unknown'
        }
