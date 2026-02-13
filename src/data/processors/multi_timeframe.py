"""
معالجة متعدد الأطر الزمنية
Multi-Timeframe Processing
"""

import pandas as pd
from typing import Dict, List
import numpy as np


class MultiTimeframeProcessor:
    """
    معالج بيانات متعددة الأطر الزمنية
    """
    
    def __init__(self):
        self.timeframes = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240,
            'D1': 1440
        }
        
    def resample(self, df: pd.DataFrame, target_tf: str) -> pd.DataFrame:
        """
        تحويل البيانات إلى إطار زمني مختلف
        """
        if target_tf not in self.timeframes:
            raise ValueError(f"Unknown timeframe: {target_tf}")
        
        rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # تحديد الفترة
        minutes = self.timeframes[target_tf]
        freq = f'{minutes}T'
        
        resampled = df.resample(freq).agg(rules).dropna()
        
        return resampled
    
    def align_timeframes(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        محاذاة الأطر الزمنية المختلفة في DataFrame واحد
        """
        # استخدام أقل إطار زمني كأساس
        base_tf = min(data_dict.keys(), key=lambda x: self.timeframes.get(x, 999999))
        base_data = data_dict[base_tf].copy()
        
        for tf, df in data_dict.items():
            if tf == base_tf:
                continue
            
            # إعادة أخذ العينات للمطابقة
            aligned = df.reindex(base_data.index, method='ffill')
            
            # إضافة لاحقة للأعمدة
            suffix = f"_{tf}"
            for col in ['open', 'high', 'low', 'close']:
                if col in aligned.columns:
                    base_data[f"{col}{suffix}"] = aligned[col]
        
        return base_data
    
    def detect_timeframe_alignment(self, data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """
        اكتشاف محاذاة الاتجاهات عبر الأطر الزمنية
        """
        trends = {}
        
        for tf, df in data_dict.items():
            if len(df) < 20:
                continue
            
            sma_fast = df['close'].rolling(10).mean().iloc[-1]
            sma_slow = df['close'].rolling(20).mean().iloc[-1]
            
            trends[tf] = 'bullish' if sma_fast > sma_slow else 'bearish'
        
        # التحقق من التوافق
        bullish_count = sum(1 for t in trends.values() if t == 'bullish')
        bearish_count = sum(1 for t in trends.values() if t == 'bearish')
        
        return {
            'trends': trends,
            'aligned': len(set(trends.values())) == 1,
            'dominant': 'bullish' if bullish_count > bearish_count else 'bearish',
            'alignment_strength': max(bullish_count, bearish_count) / len(trends) if trends else 0
        }
