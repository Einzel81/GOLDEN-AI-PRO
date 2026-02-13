"""
تحليل نقطة التحكم (POC)
Point of Control Analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class POCAnalyzer:
    """
    محلل متقدم لـ Point of Control
    """
    
    def __init__(self, lookback_periods: int = 5):
        self.lookback_periods = lookback_periods
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل POC مع التاريخ
        """
        if len(df) < 100:
            return self._empty_result()
        
        # حساب POC لكل فترة
        pocs = []
        window_size = len(df) // self.lookback_periods
        
        for i in range(self.lookback_periods):
            start_idx = i * window_size
            end_idx = (i + 1) * window_size if i < self.lookback_periods - 1 else len(df)
            
            window = df.iloc[start_idx:end_idx]
            poc = self._calculate_poc(window)
            
            pocs.append({
                'period': i,
                'poc': poc,
                'start_time': window.index[0],
                'end_time': window.index[-1]
            })
        
        # POC الحالي
        current_poc = pocs[-1]['poc']
        current_price = df['close'].iloc[-1]
        
        return {
            'current_poc': current_poc,
            'price_vs_poc': current_price - current_poc,
            'price_position': 'above' if current_price > current_poc else 'below',
            'distance_percent': abs(current_price - current_poc) / current_poc * 100,
            'poc_history': pocs,
            'poc_migration': self._analyze_poc_migration(pocs),
            'strength': self._calculate_poc_strength(df, current_poc)
        }
    
    def _calculate_poc(self, df: pd.DataFrame) -> float:
        """حساب POC لفترة محددة"""
        # Volume Profile بسيط
        price_range = np.linspace(df['low'].min(), df['high'].max(), 50)
        
        max_volume = 0
        poc_price = df['close'].mean()
        
        for i in range(len(price_range) - 1):
            mask = (df['low'] <= price_range[i+1]) & (df['high'] >= price_range[i])
            volume = df[mask]['volume'].sum()
            
            if volume > max_volume:
                max_volume = volume
                poc_price = (price_range[i] + price_range[i+1]) / 2
        
        return poc_price
    
    def _analyze_poc_migration(self, pocs: List[Dict]) -> str:
        """تحليل هجرة POC"""
        if len(pocs) < 2:
            return 'stable'
        
        prices = [p['poc'] for p in pocs]
        
        # حساب الاتجاه
        if all(prices[i] <= prices[i+1] for i in range(len(prices)-1)):
            return 'rising'
        elif all(prices[i] >= prices[i+1] for i in range(len(prices)-1)):
            return 'falling'
        
        return 'mixed'
    
    def _calculate_poc_strength(self, df: pd.DataFrame, poc: float) -> float:
        """حساب قوة POC"""
        # القوة تعتمد على حجم التداول عند POC
        tolerance = poc * 0.005
        
        volume_at_poc = df[
            (df['low'] >= poc - tolerance) & 
            (df['high'] <= poc + tolerance)
        ]['volume'].sum()
        
        total_volume = df['volume'].sum()
        
        return volume_at_poc / total_volume if total_volume > 0 else 0
    
    def _empty_result(self) -> Dict:
        """نتيجة فارغة"""
        return {
            'current_poc': 0,
            'price_vs_poc': 0,
            'price_position': 'unknown',
            'poc_history': [],
            'poc_migration': 'unknown',
            'strength': 0
        }
