"""
حماية من الخسارة المتتالية
Drawdown Protection System
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger


class ProtectionLevel(Enum):
    """مستويات الحماية"""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    LOCKDOWN = "lockdown"


@dataclass
class DrawdownStatus:
    """حالة التراجع"""
    current_drawdown: float
    max_drawdown: float
    daily_drawdown: float
    consecutive_losses: int
    protection_level: ProtectionLevel
    trading_allowed: bool
    recommended_risk: float


class DrawdownProtection:
    """
    نظام حماية متقدم من الخسارة المتتالية
    """
    
    def __init__(
        self,
        max_daily_drawdown: float = 0.05,      # 5%
        max_total_drawdown: float = 0.20,       # 20%
        max_consecutive_losses: int = 5,
        risk_reduction_steps: List[float] = None
    ):
        self.max_daily_dd = max_daily_drawdown
        self.max_total_dd = max_total_drawdown
        self.max_consecutive = max_consecutive_losses
        
        self.risk_steps = risk_reduction_steps or [1.0, 0.7, 0.5, 0.3, 0.0]
        
        self.peak_balance = 0.0
        self.daily_start_balance = 0.0
        self.current_balance = 0.0
        self.consecutive_losses = 0
        self.loss_streaks: List[Dict] = []
        self.last_trade_date = datetime.now().date()
        
    def update(self, trade_result: Dict):
        """
        تحديث الحالة بعد صفقة
        """
        pnl = trade_result.get('pnl', 0)
        self.current_balance = trade_result.get('balance', self.current_balance)
        
        # تحديث الذروة
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # إعادة تعيين اليومي إذا كان يوم جديد
        current_date = datetime.now().date()
        if current_date != self.last_trade_date:
            self.daily_start_balance = self.current_balance
            self.last_trade_date = current_date
        
        # تحديث الخسارة المتتالية
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            if self.consecutive_losses >= 3:
                self.loss_streaks.append({
                    'length': self.consecutive_losses,
                    'date': datetime.now(),
                    'recovered': True
                })
            self.consecutive_losses = 0
        
        # التحقق من الحدود
        self._check_limits()
    
    def get_status(self) -> DrawdownStatus:
        """
        الحصول على حالة الحماية الحالية
        """
        current_dd = self._calculate_drawdown()
        daily_dd = self._calculate_daily_drawdown()
        
        level = self._determine_protection_level(current_dd, daily_dd)
        allowed = level != ProtectionLevel.LOCKDOWN
        recommended_risk = self._get_recommended_risk(level)
        
        return DrawdownStatus(
            current_drawdown=current_dd,
            max_drawdown=self.max_total_dd,
            daily_drawdown=daily_dd,
            consecutive_losses=self.consecutive_losses,
            protection_level=level,
            trading_allowed=allowed,
            recommended_risk=recommended_risk
        )
    
    def _calculate_drawdown(self) -> float:
        """حساب التراجع الحالي"""
        if self.peak_balance <= 0:
            return 0.0
        return (self.peak_balance - self.current_balance) / self.peak_balance
    
    def _calculate_daily_drawdown(self) -> float:
        """حساب التراجع اليومي"""
        if self.daily_start_balance <= 0:
            return 0.0
        return (self.daily_start_balance - self.current_balance) / self.daily_start_balance
    
    def _determine_protection_level(
        self,
        current_dd: float,
        daily_dd: float
    ) -> ProtectionLevel:
        """تحديد مستوى الحماية"""
        
        # فحص الخسارة المتتالية
        if self.consecutive_losses >= self.max_consecutive:
            return ProtectionLevel.LOCKDOWN
        
        # فحص التراجع اليومي
        if daily_dd >= self.max_daily_dd:
            return ProtectionLevel.CRITICAL
        
        # فحص التراجع الكلي
        if current_dd >= self.max_total_dd:
            return ProtectionLevel.LOCKDOWN
        
        if current_dd >= self.max_total_dd * 0.75:
            return ProtectionLevel.CRITICAL
        
        if current_dd >= self.max_total_dd * 0.5:
            return ProtectionLevel.WARNING
        
        if current_dd >= self.max_total_dd * 0.25:
            return ProtectionLevel.CAUTION
        
        if self.consecutive_losses >= 3:
            return ProtectionLevel.CAUTION
        
        return ProtectionLevel.NORMAL
    
    def _get_recommended_risk(self, level: ProtectionLevel) -> float:
        """الحصول على المخاطرة الموصى بها"""
        risk_map = {
            ProtectionLevel.NORMAL: self.risk_steps[0],
            ProtectionLevel.CAUTION: self.risk_steps[1],
            ProtectionLevel.WARNING: self.risk_steps[2],
            ProtectionLevel.CRITICAL: self.risk_steps[3],
            ProtectionLevel.LOCKDOWN: self.risk_steps[4]
        }
        return risk_map.get(level, 0.0)
    
    def _check_limits(self):
        """التحقق من الحدود وإرسال التنبيهات"""
        status = self.get_status()
        
        if status.protection_level == ProtectionLevel.CRITICAL:
            logger.critical(
                f"CRITICAL DRAWDOWN: {status.current_drawdown:.2%} | "
                f"Trading restricted to {status.recommended_risk:.0%} risk"
            )
        elif status.protection_level == ProtectionLevel.WARNING:
            logger.warning(
                f"High drawdown: {status.current_drawdown:.2%} | "
                f"Risk reduced to {status.recommended_risk:.0%}"
            )
    
    def can_trade(self) -> bool:
        """التحقق مما إذا كان مسموحاً بالتداول"""
        return self.get_status().trading_allowed
    
    def get_cooldown_period(self) -> int:
        """الحصول على فترة الانتظار (بالدقائق)"""
        status = self.get_status()
        
        cooldown_map = {
            ProtectionLevel.NORMAL: 0,
            ProtectionLevel.CAUTION: 15,
            ProtectionLevel.WARNING: 60,
            ProtectionLevel.CRITICAL: 240,  # 4 ساعات
            ProtectionLevel.LOCKDOWN: 1440  # 24 ساعة
        }
        
        return cooldown_map.get(status.protection_level, 0)
    
    def get_recovery_plan(self) -> Dict:
        """خطة التعافي"""
        status = self.get_status()
        
        if status.protection_level == ProtectionLevel.NORMAL:
            return {'action': 'continue_normal', 'steps': []}
        
        steps = []
        
        if status.consecutive_losses > 0:
            steps.append(f"Stop trading for {self.get_cooldown_period()} minutes")
            steps.append("Review recent trades for pattern analysis")
        
        if status.current_drawdown > 0.1:
            steps.append("Reduce position size by 50%")
            steps.append("Focus on high-confidence setups only")
        
        if status.daily_drawdown > 0.03:
            steps.append("Close all positions and reassess")
        
        return {
            'current_status': status.protection_level.value,
            'action': 'reduce_risk' if status.protection_level != ProtectionLevel.LOCKDOWN else 'stop_trading',
            'steps': steps,
            'target_drawdown': status.max_drawdown * 0.5
        }
    
    def reset_daily(self):
        """إعادة تعيين الإحصائيات اليومية"""
        self.daily_start_balance = self.current_balance
        self.last_trade_date = datetime.now().date()
        logger.info("Daily drawdown stats reset")
    
    def get_stats(self) -> Dict:
        """إحصائيات كاملة"""
        status = self.get_status()
        
        return {
            'current_drawdown': f"{status.current_drawdown:.2%}",
            'daily_drawdown': f"{status.daily_drawdown:.2%}",
            'max_allowed_drawdown': f"{status.max_drawdown:.2%}",
            'consecutive_losses': status.consecutive_losses,
            'protection_level': status.protection_level.value,
            'trading_allowed': status.trading_allowed,
            'recommended_risk': f"{status.recommended_risk:.0%}",
            'cooldown_minutes': self.get_cooldown_period(),
            'loss_streaks_history': len(self.loss_streaks)
        }
