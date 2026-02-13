"""
محلل الانزلاق السعري
Slippage Analyzer
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import deque
from loguru import logger


@dataclass
class SlippageRecord:
    """سجل انزلاق"""
    timestamp: datetime
    symbol: str
    expected_price: float
    executed_price: float
    slippage_pips: float
    slippage_percent: float
    order_type: str  # market, limit, stop
    volume: float
    spread_at_execution: float


class SlippageAnalyzer:
    """
    محلل الانزلاق السعري للأوامر
    """
    
    def __init__(self, max_history: int = 1000):
        self.records: deque = deque(maxlen=max_history)
        self.benchmarks = {
            'excellent': 0.1,   # 0.1 pip
            'good': 0.5,        # 0.5 pip
            'acceptable': 1.0,  # 1 pip
            'poor': 2.0         # 2 pips
        }
        
    def record_slippage(
        self,
        symbol: str,
        expected_price: float,
        executed_price: float,
        order_type: str,
        volume: float,
        spread: float
    ):
        """تسجيل انزلاق"""
        
        # حساب الانزلاق
        slippage = abs(executed_price - expected_price)
        slippage_percent = (slippage / expected_price) * 100
        
        # تحويل إلى نقاط (pips) لـ XAUUSD
        slippage_pips = slippage / 0.01
        
        record = SlippageRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            expected_price=expected_price,
            executed_price=executed_price,
            slippage_pips=slippage_pips,
            slippage_percent=slippage_percent,
            order_type=order_type,
            volume=volume,
            spread_at_execution=spread
        )
        
        self.records.append(record)
        
        # تسجيل إذا كان الانزلاق كبيراً
        if slippage_pips > self.benchmarks['poor']:
            logger.warning(
                f"High slippage detected: {slippage_pips:.2f} pips | "
                f"Expected: {expected_price}, Got: {executed_price}"
            )
        
        return record
    
    def get_statistics(self, n_recent: int = 100) -> Dict:
        """إحصائيات الانزلاق"""
        if not self.records:
            return self._empty_stats()
        
        recent = list(self.records)[-n_recent:]
        slippages = [r.slippage_pips for r in recent]
        
        return {
            'sample_size': len(recent),
            'average_slippage_pips': pd.Series(slippages).mean(),
            'median_slippage_pips': pd.Series(slippages).median(),
            'max_slippage_pips': max(slippages),
            'min_slippage_pips': min(slippages),
            'std_slippage_pips': pd.Series(slippages).std(),
            'percentile_95': pd.Series(slippages).quantile(0.95),
            'percentile_99': pd.Series(slippages).quantile(0.99),
            'by_order_type': self._stats_by_order_type(recent),
            'quality_distribution': self._quality_distribution(slippages)
        }
    
    def _stats_by_order_type(self, records: List[SlippageRecord]) -> Dict:
        """إحصائيات حسب نوع الأمر"""
        by_type = {}
        
        for order_type in ['market', 'limit', 'stop']:
            type_records = [r for r in records if r.order_type == order_type]
            if type_records:
                slippages = [r.slippage_pips for r in type_records]
                by_type[order_type] = {
                    'count': len(type_records),
                    'avg_slippage': pd.Series(slippages).mean(),
                    'max_slippage': max(slippages)
                }
        
        return by_type
    
    def _quality_distribution(self, slippages: List[float]) -> Dict:
        """توزيع جودة التنفيذ"""
        total = len(slippages)
        if total == 0:
            return {}
        
        excellent = sum(1 for s in slippages if s <= self.benchmarks['excellent'])
        good = sum(1 for s in slippages if self.benchmarks['excellent'] < s <= self.benchmarks['good'])
        acceptable = sum(1 for s in slippages if self.benchmarks['good'] < s <= self.benchmarks['acceptable'])
        poor = sum(1 for s in slippages if s > self.benchmarks['acceptable'])
        
        return {
            'excellent': {'count': excellent, 'percent': excellent / total * 100},
            'good': {'count': good, 'percent': good / total * 100},
            'acceptable': {'count': acceptable, 'percent': acceptable / total * 100},
            'poor': {'count': poor, 'percent': poor / total * 100}
        }
    
    def get_slippage_estimate(self, order_type: str = 'market', volume: float = 0.1) -> float:
        """تقدير الانزلاق المتوقع"""
        if not self.records:
            return 0.5  # تقدير افتراضي
        
        # فلترة حسب نوع الأمر
        relevant = [r for r in self.records if r.order_type == order_type]
        
        if not relevant:
            relevant = list(self.records)
        
        # حساب المتوسط المرجح بالحجم
        weighted_slippage = sum(
            r.slippage_pips * (r.volume / volume if volume > 0 else 1)
            for r in relevant[-50:]
        ) / len(relevant[-50:])
        
        return weighted_slippage
    
    def should_adjust_entry(self, slippage_pips: float) -> bool:
        """التحقق مما إذا كان يجب تعديل سعر الدخول"""
        return slippage_pips > self.benchmarks['acceptable']
    
    def recommend_order_type(self, urgency: str = 'normal') -> str:
        """توصية بنوع الأمر الأمثل"""
        stats = self.get_statistics()
        
        by_type = stats.get('by_order_type', {})
        
        if urgency == 'high':
            return 'market'  # السرعة أولوية
        
        # مقارنة الأنواع
        market_avg = by_type.get('market', {}).get('avg_slippage', 1.0)
        limit_avg = by_type.get('limit', {}).get('avg_slippage', 0.3)
        
        if limit_avg < market_avg * 0.5:
            return 'limit'
        
        return 'market'
    
    def _empty_stats(self) -> Dict:
        """إحصائيات فارغة"""
        return {
            'sample_size': 0,
            'average_slippage_pips': 0,
            'median_slippage_pips': 0,
            'max_slippage_pips': 0,
            'min_slippage_pips': 0,
            'by_order_type': {},
            'quality_distribution': {}
        }
    
    def export_report(self, filepath: str):
        """تصدير تقرير"""
        stats = self.get_statistics(len(self.records))
        
        with open(filepath, 'w') as f:
            f.write("Slippage Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Sample Size: {stats['sample_size']}\n")
            f.write(f"Average Slippage: {stats['average_slippage_pips']:.2f} pips\n")
            f.write(f"Median Slippage: {stats['median_slippage_pips']:.2f} pips\n")
            f.write(f"95th Percentile: {stats['percentile_95']:.2f} pips\n\n")
            
            f.write("Quality Distribution:\n")
            for quality, data in stats['quality_distribution'].items():
                f.write(f"  {quality}: {data['percent']:.1f}%\n")
