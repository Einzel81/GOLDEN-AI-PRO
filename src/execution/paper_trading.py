"""
التداول الورقي (محاكاة)
Paper Trading Simulator
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np
from loguru import logger


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    CLOSED = "closed"


@dataclass
class PaperOrder:
    """أمر تداول ورقي"""
    id: str
    symbol: str
    action: str  # buy, sell
    volume: float
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: OrderStatus
    open_time: datetime
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0


class PaperTradingSimulator:
    """
    محاكي تداول ورقي واقعي
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        spread_pips: float = 2.0,
        commission_per_lot: float = 7.0,
        slippage_std: float = 0.1
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions: List[PaperOrder] = []
        self.closed_positions: List[PaperOrder] = []
        self.spread = spread_pips * 0.01  # تحويل إلى سعر
        self.commission = commission_per_lot
        self.slippage_std = slippage_std
        
        self.trade_history: List[Dict] = []
        
    def open_position(
        self,
        symbol: str,
        action: str,
        volume: float,
        current_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> PaperOrder:
        """فتح مركز"""
        
        # حساب الانزلاق العشوائي
        slippage = np.random.normal(0, self.slippage_std)
        
        # حساب سعر الدخول مع السبريد
        if action == 'buy':
            entry_price = current_price + self.spread + slippage
        else:
            entry_price = current_price - self.spread - slippage
        
        # حساب العمولة
        commission = self.commission * volume
        
        # التحقق من الرصيد
        margin_required = entry_price * volume * 100 / 100  # افتراض رافعة 1:100
        if margin_required > self.balance * 0.9:
            logger.warning("Insufficient margin for paper trade")
            return None
        
        order = PaperOrder(
            id=f"PAPER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.positions)}",
            symbol=symbol,
            action=action,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.FILLED,
            open_time=datetime.now()
        )
        
        self.positions.append(order)
        self.balance -= commission
        
        logger.info(
            f"Paper position opened: {action} {volume} {symbol} @ {entry_price:.2f}"
        )
        
        return order
    
    def update_positions(self, current_price: float):
        """تحديث المراكز مع السعر الحالي"""
        for position in self.positions:
            if position.status != OrderStatus.FILLED:
                continue
            
            # حساب الربح/الخسارة غير المحقق
            if position.action == 'buy':
                unrealized_pnl = (current_price - position.entry_price) * position.volume * 100
                # التحقق من SL/TP
                if position.stop_loss and current_price <= position.stop_loss:
                    self.close_position(position.id, position.stop_loss)
                elif position.take_profit and current_price >= position.take_profit:
                    self.close_position(position.id, position.take_profit)
            else:
                unrealized_pnl = (position.entry_price - current_price) * position.volume * 100
                # التحقق من SL/TP
                if position.stop_loss and current_price >= position.stop_loss:
                    self.close_position(position.id, position.stop_loss)
                elif position.take_profit and current_price <= position.take_profit:
                    self.close_position(position.id, position.take_profit)
            
            # تحديث Equity
            self.equity = self.balance + sum(
                self._calculate_unrealized_pnl(p, current_price) 
                for p in self.positions 
                if p.status == OrderStatus.FILLED
            )
    
    def close_position(
        self,
        position_id: str,
        close_price: Optional[float] = None
    ) -> Optional[PaperOrder]:
        """إغلاق مركز"""
        position = next((p for p in self.positions if p.id == position_id), None)
        
        if not position or position.status != OrderStatus.FILLED:
            return None
        
        # حساب سعر الإغلاق
        if close_price is None:
            # استخدام السعر الحالي مع انزلاق
            slippage = np.random.normal(0, self.slippage_std)
            close_price = position.entry_price + slippage
        
        # حساب العمولة
        commission = self.commission * position.volume
        
        # حساب الربح/الخسارة
        if position.action == 'buy':
            pnl = (close_price - position.entry_price) * position.volume * 100
        else:
            pnl = (position.entry_price - close_price) * position.volume * 100
        
        pnl -= commission * 2  # عمولتان (دخول وخروج)
        
        # تحديث المركز
        position.close_price = close_price
        position.close_time = datetime.now()
        position.pnl = pnl
        position.pnl_percent = (pnl / (position.entry_price * position.volume * 100)) * 100
        position.status = OrderStatus.CLOSED
        
        # تحديث الرصيد
        self.balance += pnl
        self.equity = self.balance
        
        # نقل إلى المراكز المغلقة
        self.positions.remove(position)
        self.closed_positions.append(position)
        
        # تسجيل
        self.trade_history.append({
            'id': position.id,
            'symbol': position.symbol,
            'action': position.action,
            'volume': position.volume,
            'entry': position.entry_price,
            'exit': close_price,
            'pnl': pnl,
            'pnl_percent': position.pnl_percent,
            'duration': (position.close_time - position.open_time).total_seconds() / 60
        })
        
        logger.info(
            f"Paper position closed: {position.id} | PnL: ${pnl:.2f} ({position.pnl_percent:.2f}%)"
        )
        
        return position
    
    def _calculate_unrealized_pnl(self, position: PaperOrder, current_price: float) -> float:
        """حساب الربح/الخسارة غير المحقق"""
        if position.action == 'buy':
            return (current_price - position.entry_price) * position.volume * 100
        return (position.entry_price - current_price) * position.volume * 100
    
    def get_account_summary(self) -> Dict:
        """ملخص الحساب"""
        total_trades = len(self.closed_positions)
        winning_trades = len([p for p in self.closed_positions if p.pnl > 0])
        losing_trades = total_trades - winning_trades
        
        total_pnl = self.balance - self.initial_balance
        total_return = (total_pnl / self.initial_balance) * 100
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': round(self.balance, 2),
            'equity': round(self.equity, 2),
            'total_pnl': round(total_pnl, 2),
            'total_return_percent': round(total_return, 2),
            'open_positions': len(self.positions),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0,
            'avg_pnl_per_trade': round(total_pnl / total_trades, 2) if total_trades > 0 else 0
        }
    
    def get_performance_report(self) -> Dict:
        """تقرير الأداء"""
        if not self.closed_positions:
            return {'message': 'No trades yet'}
        
        pnls = [p.pnl for p in self.closed_positions]
        
        return {
            'total_return': f"{((self.balance - self.initial_balance) / self.initial_balance * 100):.2f}%",
            'sharpe_ratio': self._calculate_sharpe(),
            'max_drawdown': self._calculate_max_drawdown(),
            'profit_factor': self._calculate_profit_factor(),
            'average_trade': f"${np.mean(pnls):.2f}",
            'best_trade': f"${max(pnls):.2f}",
            'worst_trade': f"${min(pnls):.2f}",
            'avg_holding_time': self._calculate_avg_holding_time()
        }
    
    def _calculate_sharpe(self, risk_free_rate: float = 0.0) -> float:
        """حساب نسبة Sharpe"""
        if len(self.closed_positions) < 2:
            return 0.0
        
        returns = [p.pnl_percent for p in self.closed_positions]
        excess_returns = np.array(returns) - risk_free_rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns)
    
    def _calculate_max_drawdown(self) -> str:
        """حساب أقصى تراجع"""
        equity_curve = [self.initial_balance]
        for trade in self.closed_positions:
            equity_curve.append(equity_curve[-1] + trade.pnl)
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_dd = max(max_dd, drawdown)
        
        return f"{max_dd:.2%}"
    
    def _calculate_profit_factor(self) -> float:
        """حساب معامل الربح"""
        gross_profit = sum(p.pnl for p in self.closed_positions if p.pnl > 0)
        gross_loss = abs(sum(p.pnl for p in self.closed_positions if p.pnl < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def _calculate_avg_holding_time(self) -> str:
        """حساب متوسط وقت الاحتفاظ"""
        if not self.closed_positions:
            return "0 min"
        
        durations = [
            (p.close_time - p.open_time).total_seconds() / 60 
            for p in self.closed_positions
        ]
        
        avg_minutes = np.mean(durations)
        
        if avg_minutes < 60:
            return f"{avg_minutes:.0f} min"
        else:
            return f"{avg_minutes / 60:.1f} hours"
    
    def reset(self):
        """إعادة تعيين المحاكي"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.positions = []
        self.closed_positions = []
        self.trade_history = []
        logger.info("Paper trading simulator reset")
