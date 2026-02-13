"""
حساب حجم المركز
Position Sizing Algorithms
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class SizingMethod(Enum):
    FIXED_FRACTIONAL = "fixed_fractional"
    FIXED_RATIO = "fixed_ratio"
    KELLY_CRITERION = "kelly_criterion"
    OPTIMAL_F = "optimal_f"
    VOLATILITY_BASED = "volatility_based"


@dataclass
class PositionSize:
    """حجم المركز المحسوب"""
    lots: float
    units: float
    risk_amount: float
    risk_percent: float
    method: str


class PositionSizer:
    """
    حاسب حجم المركز باستخدام طرق متعددة:
    - Fixed Fractional
    - Kelly Criterion
    - Volatility-Based
    """
    
    def __init__(self, account_balance: float):
        self.balance = account_balance
        self.equity = account_balance
        
    def calculate(
        self,
        entry_price: float,
        stop_loss: float,
        method: SizingMethod = SizingMethod.FIXED_FRACTIONAL,
        risk_percent: float = 0.02,
        **kwargs
    ) -> PositionSize:
        """
        حساب حجم المركز
        """
        if method == SizingMethod.FIXED_FRACTIONAL:
            return self._fixed_fractional(entry_price, stop_loss, risk_percent)
        
        elif method == SizingMethod.KELLY_CRITERION:
            win_rate = kwargs.get('win_rate', 0.5)
            win_loss_ratio = kwargs.get('win_loss_ratio', 1.0)
            return self._kelly_criterion(entry_price, stop_loss, win_rate, win_loss_ratio)
        
        elif method == SizingMethod.VOLATILITY_BASED:
            atr = kwargs.get('atr', 0)
            return self._volatility_based(entry_price, stop_loss, atr, risk_percent)
        
        else:
            return self._fixed_fractional(entry_price, stop_loss, risk_percent)
    
    def _fixed_fractional(
        self,
        entry: float,
        stop: float,
        risk_percent: float
    ) -> PositionSize:
        """طريقة Fixed Fractional"""
        risk_amount = self.balance * risk_percent
        stop_distance = abs(entry - stop)
        
        if stop_distance == 0:
            return PositionSize(0, 0, 0, 0, "fixed_fractional")
        
        # XAUUSD: 1 lot = 100 oz, 1 pip = $10 for 1 lot (تقريبي)
        # حساب موحد
        position_value = risk_amount / stop_distance
        lots = position_value / 100  # تحويل إلى lots
        
        # الحدود
        lots = max(0.01, min(lots, 10.0))
        
        return PositionSize(
            lots=round(lots, 2),
            units=lots * 100,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            method="fixed_fractional"
        )
    
    def _kelly_criterion(
        self,
        entry: float,
        stop: float,
        win_rate: float,
        win_loss_ratio: float,
        fraction: float = 0.5
    ) -> PositionSize:
        """معيار كيلي (نصف كيلي للتحفظ)"""
        # f* = (p*b - q) / b
        # p: win rate, q: loss rate (1-p), b: win/loss ratio
        
        if win_loss_ratio <= 0:
            return self._fixed_fractional(entry, stop, 0.01)
        
        q = 1 - win_rate
        kelly_f = (win_rate * win_loss_ratio - q) / win_loss_ratio
        
        # نصف كيلي للتحفظ
        kelly_f *= fraction
        
        # الحدود الآمنة
        kelly_f = max(0, min(kelly_f, 0.25))
        
        risk_amount = self.balance * kelly_f
        stop_distance = abs(entry - stop)
        
        if stop_distance == 0:
            return PositionSize(0, 0, 0, 0, "kelly_criterion")
        
        position_value = risk_amount / stop_distance
        lots = position_value / 100
        
        return PositionSize(
            lots=round(lots, 2),
            units=lots * 100,
            risk_amount=risk_amount,
            risk_percent=kelly_f,
            method="kelly_criterion"
        )
    
    def _volatility_based(
        self,
        entry: float,
        stop: float,
        atr: float,
        base_risk: float
    ) -> PositionSize:
        """حجم مركز مبني على التقلب"""
        if atr <= 0:
            return self._fixed_fractional(entry, stop, base_risk)
        
        # تعديل المخاطر بناءً على التقلب
        # تقلب عالي = حجم أصغر
        volatility_factor = 0.02 / (atr / entry)  # تطبيع
        
        adjusted_risk = base_risk * min(volatility_factor, 1.5)
        adjusted_risk = max(0.005, min(adjusted_risk, 0.05))
        
        return self._fixed_fractional(entry, stop, adjusted_risk)
    
    def update_balance(self, new_balance: float):
        """تحديث رصيد الحساب"""
        self.balance = new_balance
    
    def get_max_position_size(self, symbol: str = "XAUUSD") -> float:
        """الحصول على الحد الأقصى لحجم المركز"""
        # 5% من رصيد الحساب كحد أقصى
        max_risk = self.balance * 0.05
        
        # تقريباً لـ XAUUSD
        return max_risk / 1000  # lots
    
    def calculate_portfolio_heat(
        self,
        open_positions: list,
        correlation_matrix: Optional[np.ndarray] = None
    ) -> Dict:
        """
        حساب حرارة المحفظة (إجمالي المخاطر)
        """
        total_risk = sum(pos.risk_amount for pos in open_positions)
        total_risk_percent = total_risk / self.balance
        
        # تعديل حسب الارتباط
        if correlation_matrix is not None and len(open_positions) > 1:
            # تقليل المخاطر إذا كانت المراكز مترابطة سلبياً
            avg_correlation = np.mean(correlation_matrix)
            diversification_factor = 1 - (avg_correlation * 0.5)
            adjusted_risk = total_risk_percent * diversification_factor
        else:
            adjusted_risk = total_risk_percent
        
        return {
            'total_risk_amount': total_risk,
            'total_risk_percent': total_risk_percent,
            'adjusted_risk_percent': adjusted_risk,
            'remaining_capacity': 0.20 - adjusted_risk,  # 20% max heat
            'can_add_position': adjusted_risk < 0.20
        }
