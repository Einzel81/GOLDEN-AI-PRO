"""
Volume Profile Analysis
تحليل بروفايل الحجم
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class VolumeNode:
    """عقدة حجم"""
    price_level: float
    volume: float
    normalized_volume: float


class VolumeProfileAnalyzer:
    """
    محلل Volume Profile مع:
    - حساب POC (Point of Control)
    - Value Area (VAH/VAL)
    - Volume Nodes
    """
    
    def __init__(self, num_bins: int = 24):
        self.num_bins = num_bins
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل Volume Profile
        """
        if len(df) < 10:
            return self._empty_result()
        
        # إنشاء bins للأسعار
        price_bins = np.linspace(df['low'].min(), df['high'].max(), self.num_bins)
        
        # حساب الحجم لكل مستوى سعري
        volume_nodes = self._calculate_volume_nodes(df, price_bins)
        
        # إيجاد POC
        poc = self._find_poc(volume_nodes)
        
        # حساب Value Area
        vah, val = self._calculate_value_area(volume_nodes, poc)
        
        # تحديد High/Low Volume Nodes
        hvn, lvn = self._classify_nodes(volume_nodes)
        
        return {
            'poc': poc,
            'vah': vah,
            'val': val,
            'value_area_width': ((vah - val) / poc) * 100 if poc > 0 else 0,
            'volume_nodes': [self._node_to_dict(n) for n in volume_nodes],
            'hvn': [self._node_to_dict(n) for n in hvn],
            'lvn': [self._node_to_dict(n) for n in lvn],
            'current_price_position': self._price_position(df['close'].iloc[-1], vah, val)
        }
    
    def _calculate_volume_nodes(
        self,
        df: pd.DataFrame,
        price_bins: np.ndarray
    ) -> List[VolumeNode]:
        """حساب العقد الحجمية"""
        nodes = []
        total_volume = df['volume'].sum()
        
        for i in range(len(price_bins) - 1):
            low = price_bins[i]
            high = price_bins[i + 1]
            mid_price = (low + high) / 2
            
            # حساب الحجم في هذا النطاق
            mask = (df['low'] <= high) & (df['high'] >= low)
            volume = df[mask]['volume'].sum()
            
            normalized = volume / total_volume if total_volume > 0 else 0
            
            nodes.append(VolumeNode(
                price_level=mid_price,
                volume=volume,
                normalized_volume=normalized
            ))
        
        return nodes
    
    def _find_poc(self, nodes: List[VolumeNode]) -> float:
        """إيجاد Point of Control"""
        if not nodes:
            return 0.0
        
        poc_node = max(nodes, key=lambda x: x.volume)
        return poc_node.price_level
    
    def _calculate_value_area(
        self,
        nodes: List[VolumeNode],
        poc: float,
        va_percent: float = 0.70
    ) -> Tuple[float, float]:
        """حساب Value Area (70% من الحجم)"""
        if not nodes:
            return 0.0, 0.0
        
        # ترتيب العقد حسب البعد عن POC
        sorted_nodes = sorted(nodes, key=lambda x: abs(x.price_level - poc))
        
        # جمع الحجم حتى الوصول إلى النسبة المطلوبة
        cumulative_volume = 0.0
        total_volume = sum(n.volume for n in nodes)
        target_volume = total_volume * va_percent
        
        selected_prices = []
        
        for node in sorted_nodes:
            cumulative_volume += node.volume
            selected_prices.append(node.price_level)
            
            if cumulative_volume >= target_volume:
                break
        
        if not selected_prices:
            return poc, poc
        
        return max(selected_prices), min(selected_prices)
    
    def _classify_nodes(
        self,
        nodes: List[VolumeNode]
    ) -> Tuple[List[VolumeNode], List[VolumeNode]]:
        """تصنيف العقد إلى HVN و LVN"""
        if not nodes:
            return [], []
        
        volumes = [n.normalized_volume for n in nodes]
        mean_vol = np.mean(volumes)
        std_vol = np.std(volumes)
        
        hvn = [n for n in nodes if n.normalized_volume > mean_vol + 0.5 * std_vol]
        lvn = [n for n in nodes if n.normalized_volume < mean_vol - 0.5 * std_vol]
        
        return hvn, lvn
    
    def _price_position(self, current_price: float, vah: float, val: float) -> str:
        """تحديد موقع السعر الحالي بالنسبة لـ Value Area"""
        if current_price > vah:
            return "above_va"
        elif current_price < val:
            return "below_va"
        else:
            return "inside_va"
    
    def _node_to_dict(self, node: VolumeNode) -> Dict:
        """تحويل العقدة إلى قاموس"""
        return {
            'price': round(node.price_level, 2),
            'volume': round(node.volume, 2),
            'normalized': round(node.normalized_volume, 4)
        }
    
    def _empty_result(self) -> Dict:
        """نتيجة فارغة"""
        return {
            'poc': 0.0,
            'vah': 0.0,
            'val': 0.0,
            'value_area_width': 0.0,
            'volume_nodes': [],
            'hvn': [],
            'lvn': [],
            'current_price_position': 'unknown'
        }
