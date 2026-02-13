"""
محرك التنفيذ الذكي
Smart Execution Engine
"""

import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from loguru import logger

from src.execution.order_manager import OrderManager
from src.execution.slippage_analyzer import SlippageAnalyzer
from src.data.connectors.mt5_connector import mt5_connector


class ExecutionStrategy(Enum):
    """استراتيجيات التنفيذ"""
    IMMEDIATE = "immediate"           # تنفيذ فوري
    TWAP = "twap"                    # Time-Weighted Average Price
    VWAP = "vwap"                    # Volume-Weighted Average Price
    ICEBERG = "iceberg"              # تنفيذ مخفي
    SMART = "smart"                  # ذكي (اختيار أفضل طريقة)


@dataclass
class ExecutionPlan:
    """خطة تنفيذ"""
    strategy: ExecutionStrategy
    slices: int
    interval_seconds: float
    slice_size: float
    price_limit: Optional[float]


class ExecutionEngine:
    """
    محرك تنفيذ متقدم مع استراتيجيات متعددة
    """
    
    def __init__(self, order_manager: OrderManager):
        self.order_manager = order_manager
        self.slippage_analyzer = SlippageAnalyzer()
        self.active_executions: Dict[str, asyncio.Task] = {}
        
    async def execute(
        self,
        symbol: str,
        action: str,
        total_volume: float,
        strategy: ExecutionStrategy = ExecutionStrategy.SMART,
        max_slippage: float = 2.0,
        time_limit_seconds: float = 60.0
    ) -> Dict:
        """
        تنفيذ أمر باستخدام الاستراتيجية المختارة
        """
        
        # اختيار الاستراتيجية الذكية إذا مطلوب
        if strategy == ExecutionStrategy.SMART:
            strategy = self._select_strategy(total_volume)
        
        # إنشاء خطة التنفيذ
        plan = self._create_execution_plan(
            strategy, total_volume, time_limit_seconds
        )
        
        logger.info(
            f"Starting {strategy.value} execution: {total_volume} lots "
            f"in {plan.slices} slices"
        )
        
        # تنفيذ الخطة
        if strategy == ExecutionStrategy.IMMEDIATE:
            return await self._execute_immediate(symbol, action, total_volume)
        
        elif strategy == ExecutionStrategy.TWAP:
            return await self._execute_twap(symbol, action, plan)
        
        elif strategy == ExecutionStrategy.ICEBERG:
            return await self._execute_iceberg(symbol, action, plan)
        
        else:
            return await self._execute_immediate(symbol, action, total_volume)
    
    def _select_strategy(self, volume: float) -> ExecutionStrategy:
        """اختيار أفضل استراتيجية"""
        if volume <= 0.5:
            return ExecutionStrategy.IMMEDIATE
        elif volume <= 2.0:
            return ExecutionStrategy.TWAP
        else:
            return ExecutionStrategy.ICEBERG
    
    def _create_execution_plan(
        self,
        strategy: ExecutionStrategy,
        total_volume: float,
        time_limit: float
    ) -> ExecutionPlan:
        """إنشاء خطة التنفيذ"""
        
        if strategy == ExecutionStrategy.TWAP:
            slices = min(int(time_limit / 10), 10)  # كل 10 ثواني
            return ExecutionPlan(
                strategy=strategy,
                slices=slices,
                interval_seconds=time_limit / slices,
                slice_size=total_volume / slices,
                price_limit=None
            )
        
        elif strategy == ExecutionStrategy.ICEBERG:
            slice_size = 0.5  # 0.5 lot per slice
            slices = int(total_volume / slice_size) + 1
            return ExecutionPlan(
                strategy=strategy,
                slices=slices,
                interval_seconds=5.0,  # 5 seconds between slices
                slice_size=min(slice_size, total_volume),
                price_limit=None
            )
        
        return ExecutionPlan(
            strategy=strategy,
            slices=1,
            interval_seconds=0,
            slice_size=total_volume,
            price_limit=None
        )
    
    async def _execute_immediate(
        self,
        symbol: str,
        action: str,
        volume: float
    ) -> Dict:
        """تنفيذ فوري"""
        order = await self.order_manager.place_order(
            symbol=symbol,
            action=action,
            volume=volume
        )
        
        return {
            'success': order.status == "filled",
            'order_id': order.id,
            'volume_filled': volume,
            'slices': 1,
            'avg_price': order.entry_price
        }
    
    async def _execute_twap(
        self,
        symbol: str,
        action: str,
        plan: ExecutionPlan
    ) -> Dict:
        """تنفيذ TWAP"""
        filled_volume = 0.0
        total_cost = 0.0
        slices_completed = 0
        
        for i in range(plan.slices):
            # جلب السعر الحالي
            tick = await mt5_connector.get_tick(symbol)
            current_price = tick['ask'] if action == 'buy' else tick['bid']
            
            # تنفيذ الشريحة
            slice_volume = min(plan.slice_size, plan.slice_size * plan.slices - filled_volume)
            
            order = await self.order_manager.place_order(
                symbol=symbol,
                action=action,
                volume=slice_volume
            )
            
            if order.status == "filled":
                filled_volume += slice_volume
                total_cost += order.entry_price * slice_volume
                slices_completed += 1
            
            # انتظار قبل الشريحة التالية
            if i < plan.slices - 1:
                await asyncio.sleep(plan.interval_seconds)
        
        avg_price = total_cost / filled_volume if filled_volume > 0 else 0
        
        return {
            'success': filled_volume > 0,
            'volume_filled': filled_volume,
            'slices': slices_completed,
            'avg_price': avg_price,
            'completion_rate': filled_volume / (plan.slice_size * plan.slices)
        }
    
    async def _execute_iceberg(
        self,
        symbol: str,
        action: str,
        plan: ExecutionPlan
    ) -> Dict:
        """تنفيذ Iceberg (إخفاء الحجم الكلي)"""
        # مشابه لـ TWAP لكن مع حجم ثابت صغير
        return await self._execute_twap(symbol, action, plan)
    
    async def cancel_execution(self, execution_id: str):
        """إلغاء تنفيذ جاري"""
        if execution_id in self.active_executions:
            self.active_executions[execution_id].cancel()
            logger.info(f"Execution {execution_id} cancelled")
    
    def get_execution_quality_report(self) -> Dict:
        """تقرير جودة التنفيذ"""
        stats = self.slippage_analyzer.get_statistics()
        
        return {
            'slippage_stats': stats,
            'recommendation': self.slippage_analyzer.recommend_order_type(),
            'avg_execution_time': 'TBD'  # يمكن إضافة التتبع
        }
