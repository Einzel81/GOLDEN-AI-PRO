"""
مدير المخاطر المتقدم
Advanced Risk Management System
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from dataclasses import dataclass
from loguru import logger

from config.settings import settings


@dataclass
class RiskParameters:
    """معاملات المخاطر"""
    max_risk_per_trade: float = 0.02  # 2%
    max_daily_drawdown: float = 0.05  # 5%
    max_total_drawdown: float = 0.20  # 20%
    max_correlated_trades: int = 2
    max_open_trades: int = 5
    use_kelly_criterion: bool = False
    kelly_fraction: float = 0.5  # Half Kelly


class RiskManager:
    """
    مدير مخاطر شامل يتضمن:
    - إدارة رأس المال
    - حماية من الخسارة المتتالية
    - تحديد حجم المركز الديناميكي
    - مراقبة الترابط بين الصفقات
    """
    
    def __init__(self):
        self.params = RiskParameters()
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.current_drawdown = 0.0
        self.consecutive_losses = 0
        self.trade_history: List[Dict] = []
        self.last_trade_date = pd.Timestamp.now().date()
        
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: Optional[float] = None,
        volatility: Optional[float] = None
    ) -> Dict:
        """
        حساب حجم المركز الأمثل
        """
        risk_per_trade = risk_percent or self.params.max_risk_per_trade
        
        # تعديل المخاطر بناءً على الظروف
        adjusted_risk = self._adjust_risk_for_conditions(risk_per_trade)
        
        # حساب المخاطرة بالدولار
        risk_amount = account_balance * adjusted_risk
        
        # حساب المسافة إلى وقف الخسارة
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance == 0:
            logger.warning("Stop loss distance is zero")
            return {'size': 0, 'risk_amount': 0, 'lots': 0}
        
        # حساب حجم المركز
        # XAUUSD: 1 lot = 100 ounces, 1 pip = $10 for 1 lot (roughly)
        # Simplified calculation
        position_size = risk_amount / stop_distance
        
        # تعديل حسب التقلب
        if volatility:
            position_size = self._adjust_for_volatility(position_size, volatility)
        
        # تحويل إلى lots (XAUUSD)
        lots = position_size / 100  # تقريبي
        
        # الحد الأقصى والأدنى
        lots = max(0.01, min(lots, 10.0))  # 0.01 to 10 lots
        
        return {
            'size': position_size,
            'lots': round(lots, 2),
            'risk_amount': risk_amount,
            'risk_percent': adjusted_risk,
            'stop_distance': stop_distance
        }
    
    def _adjust_risk_for_conditions(self, base_risk: float) -> float:
        """تعديل المخاطر بناءً على الظروف الحالية"""
        adjusted = base_risk
        
        # تقليل المخاطر بعد خسائر متتالية
        if self.consecutive_losses >= 2:
            adjusted *= (0.7 ** self.consecutive_losses)
            logger.info(f"Reducing risk due to {self.consecutive_losses} consecutive losses")
        
        # تقليل المخاطر عند اقتراب الحد الأقصى للخسارة
        if self.current_drawdown > self.params.max_total_drawdown * 0.5:
            adjusted *= 0.5
            logger.warning("Reducing risk due to high drawdown")
        
        # إعادة تعيين المخاطر يومياً
        current_date = pd.Timestamp.now().date()
        if current_date != self.last_trade_date:
            self.daily_pnl = 0.0
            self.last_trade_date = current_date
        
        # تقليل المخاطر إذا كنا قريبين من الحد اليومي
        if abs(self.daily_pnl) > self.params.max_daily_drawdown * 0.7:
            adjusted *= 0.5
        
        return max(adjusted, 0.005)  # الحد الأدنى 0.5%
    
    def _adjust_for_volatility(self, size: float, volatility: float) -> float:
        """تعديل الحجم بناءً على التقلب"""
        # تقليل الحجم في الأسواق المتقلبة جداً
        if volatility > 0.03:  # 3% daily volatility
            return size * 0.7
        elif volatility < 0.005:  # سوق راكد
            return size * 0.8
        return size
    
    def check_trade_allowed(self, account_balance: float, open_trades: int) -> bool:
        """التحقق مما إذا كان مسموحاً بالتداول"""
        
        # التحقق من الحد الأقصى للصفقات المفتوحة
        if open_trades >= self.params.max_open_trades:
            logger.warning("Maximum open trades reached")
            return False
        
        # التحقق من الخسارة المتتالية
        if self.consecutive_losses >= 5:
            logger.error("Trading halted due to 5 consecutive losses")
            return False
        
        # التحقق من الحد الأقصى للخسارة
        if self.current_drawdown >= self.params.max_total_drawdown:
            logger.error("Maximum drawdown reached - trading halted")
            return False
        
        # التحقق من الحد اليومي
        if self.daily_pnl <= -account_balance * self.params.max_daily_drawdown:
            logger.warning("Daily loss limit reached")
            return False
        
        return True
    
    def update_after_trade(self, trade_result: Dict):
        """تحديث الحالة بعد صفقة"""
        pnl = trade_result.get('pnl', 0)
        self.daily_pnl += pnl
        
        # تحديث الخسارة المتتالية
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # تحديث الذروة والتراجع
        current_balance = trade_result.get('balance', 0)
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        if self.peak_balance > 0:
            self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
        
        # حفظ السجل
        self.trade_history.append({
            'timestamp': pd.Timestamp.now(),
            'pnl': pnl,
            'balance': current_balance,
            'drawdown': self.current_drawdown
        })
        
        # تقليل السجل
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]
    
    def get_risk_report(self) -> Dict:
        """تقرير المخاطر الحالي"""
        return {
            'daily_pnl': self.daily_pnl,
            'current_drawdown': self.current_drawdown,
            'consecutive_losses': self.consecutive_losses,
            'open_trades_limit': self.params.max_open_trades,
            'trading_allowed': self.check_trade_allowed(10000, 0),  # Example balance
            'risk_parameters': {
                'max_risk_per_trade': self.params.max_risk_per_trade,
                'max_daily_drawdown': self.params.max_daily_drawdown,
                'max_total_drawdown': self.params.max_total_drawdown
            }
        }
    
    def calculate_correlation_risk(
        self,
        new_trade_symbol: str,
        open_trades: List[Dict]
    ) -> bool:
        """
        التحقق من مخاطر الترابط
        """
        # XAUUSD يرتبط ارتباطاً عكسياً عادةً مع:
        # - USD (DXY)
        # - أسعار الفائدة الأمريكية
        
        correlated_count = sum(
            1 for trade in open_trades
            if trade.get('symbol') == new_trade_symbol
        )
        
        if correlated_count >= self.params.max_correlated_trades:
            logger.warning(f"Maximum correlated trades for {new_trade_symbol} reached")
            return False
        
        return True
    
    def get_kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        account_balance: float
    ) -> float:
        """
        حساب حجم المركز باستخدام معيار كيلي
        """
        if not self.params.use_kelly_criterion:
            return 0.0
        
        # معادلة كيلي: f* = (p*b - q) / b
        # p: probability of win, q: probability of loss (1-p)
        # b: win/loss ratio
        
        if avg_loss == 0:
            return 0.0
        
        b = avg_win / avg_loss
        q = 1 - win_rate
        
        kelly_fraction = (win_rate * b - q) / b
        
        # Half Kelly للتحفظ
        kelly_fraction *= self.params.kelly_fraction
        
        # الحدود
        kelly_fraction = max(0, min(kelly_fraction, 0.25))
        
        return account_balance * kelly_fraction
