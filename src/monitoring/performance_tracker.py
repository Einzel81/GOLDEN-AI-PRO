"""
تتبع أداء التداول
Trading Performance Tracker
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from loguru import logger


@dataclass
class TradeMetrics:
    """مقاييس الصفقة"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    direction: str = ""  # buy/sell
    entry_price: float = 0.0
    exit_price: float = 0.0
    volume: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    holding_time_minutes: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0


class PerformanceTracker:
    """
    متتبع الأداء الشامل
    """
    
    def __init__(self, max_history: int = 10000):
        self.trades: deque = deque(maxlen=max_history)
        self.daily_stats: Dict[str, Dict] = {}
        self.current_drawdown = 0.0
        self.peak_balance = 0.0
        self.current_balance = 0.0
        
    def add_trade(self, trade: TradeMetrics):
        """إضافة صفقة"""
        self.trades.append(trade)
        
        # تحديث الإحصائيات اليومية
        date_key = trade.entry_time.strftime('%Y-%m-%d')
        if date_key not in self.daily_stats:
            self.daily_stats[date_key] = {
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'gross_profit': 0.0,
                'gross_loss': 0.0
            }
        
        stats = self.daily_stats[date_key]
        stats['trades'] += 1
        stats['total_pnl'] += trade.pnl
        
        if trade.pnl > 0:
            stats['wins'] += 1
            stats['gross_profit'] += trade.pnl
        else:
            stats['losses'] += 1
            stats['gross_loss'] += abs(trade.pnl)
        
        # تحديث الرصيد والتراجع
        self.current_balance += trade.pnl
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        if self.peak_balance > 0:
            self.current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        
        logger.info(f"Trade recorded: {trade.direction} {trade.symbol} | PnL: {trade.pnl:.2f}")
    
    def get_summary(self, days: int = 30) -> Dict:
        """ملخص الأداء"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_trades = [t for t in self.trades if t.entry_time >= cutoff]
        
        if not recent_trades:
            return self._empty_summary()
        
        pnls = [t.pnl for t in recent_trades]
        winning_trades = [t for t in recent_trades if t.pnl > 0]
        losing_trades = [t for t in recent_trades if t.pnl <= 0]
        
        total_pnl = sum(pnls)
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = sum(t.pnl for t in losing_trades)
        
        return {
            'period_days': days,
            'total_trades': len(recent_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(recent_trades) if recent_trades else 0,
            'total_pnl': round(total_pnl, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'profit_factor': abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf'),
            'average_win': np.mean([t.pnl for t in winning_trades]) if winning_trades else 0,
            'average_loss': np.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
            'largest_win': max(pnls) if pnls else 0,
            'largest_loss': min(pnls) if pnls else 0,
            'max_drawdown': self._calculate_max_drawdown(recent_trades),
            'sharpe_ratio': self._calculate_sharpe(pnls),
            'sortino_ratio': self._calculate_sortino(pnls),
            'average_holding_time': np.mean([t.holding_time_minutes for t in recent_trades]) if recent_trades else 0
        }
    
    def get_daily_report(self, date: Optional[str] = None) -> Dict:
        """تقرير يومي"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        stats = self.daily_stats.get(date, {
            'trades': 0, 'wins': 0, 'losses': 0,
            'total_pnl': 0.0, 'gross_profit': 0.0, 'gross_loss': 0.0
        })
        
        win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
        
        return {
            'date': date,
            'total_trades': stats['trades'],
            'winning_trades': stats['wins'],
            'losing_trades': stats['losses'],
            'win_rate': round(win_rate, 2),
            'total_pnl': round(stats['total_pnl'], 2),
            'net_profit': round(stats['gross_profit'] - stats['gross_loss'], 2)
        }
    
    def get_equity_curve(self) -> List[Dict]:
        """منحنى الأسهم"""
        if not self.trades:
            return []
        
        equity = 0.0
        curve = []
        
        for trade in sorted(self.trades, key=lambda x: x.entry_time):
            equity += trade.pnl
            curve.append({
                'timestamp': trade.entry_time.isoformat(),
                'equity': round(equity, 2),
                'trade_pnl': round(trade.pnl, 2)
            })
        
        return curve
    
    def get_trade_distribution(self) -> Dict:
        """توزيع الصفقات"""
        if not self.trades:
            return {}
        
        pnls = [t.pnl for t in self.trades]
        
        return {
            'by_direction': self._distribution_by_direction(),
            'by_hour': self._distribution_by_hour(),
            'by_pnl_range': self._distribution_by_pnl(pnls),
            'consecutive_wins': self._max_consecutive(lambda t: t.pnl > 0),
            'consecutive_losses': self._max_consecutive(lambda t: t.pnl <= 0)
        }
    
    def _calculate_max_drawdown(self, trades: List[TradeMetrics]) -> float:
        """حساب أقصى تراجع"""
        if not trades:
            return 0.0
        
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        
        for trade in sorted(trades, key=lambda x: x.entry_time):
            equity += trade.pnl
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)
        
        return round(max_dd, 4)
    
    def _calculate_sharpe(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """حساب نسبة Sharpe"""
        if len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def _calculate_sortino(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """حساب نسبة Sortino"""
        if len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return float('inf')
        
        return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)
    
    def _distribution_by_direction(self) -> Dict:
        """توزيع حسب الاتجاه"""
        buy_trades = [t for t in self.trades if t.direction == 'buy']
        sell_trades = [t for t in self.trades if t.direction == 'sell']
        
        return {
            'buy': {
                'count': len(buy_trades),
                'win_rate': len([t for t in buy_trades if t.pnl > 0]) / len(buy_trades) if buy_trades else 0,
                'avg_pnl': np.mean([t.pnl for t in buy_trades]) if buy_trades else 0
            },
            'sell': {
                'count': len(sell_trades),
                'win_rate': len([t for t in sell_trades if t.pnl > 0]) / len(sell_trades) if sell_trades else 0,
                'avg_pnl': np.mean([t.pnl for t in sell_trades]) if sell_trades else 0
            }
        }
    
    def _distribution_by_hour(self) -> Dict:
        """توزيع حسب الساعة"""
        hours = {}
        for trade in self.trades:
            hour = trade.entry_time.hour
            if hour not in hours:
                hours[hour] = {'trades': 0, 'wins': 0, 'total_pnl': 0}
            hours[hour]['trades'] += 1
            if trade.pnl > 0:
                hours[hour]['wins'] += 1
            hours[hour]['total_pnl'] += trade.pnl
        
        return {f"{h:02d}:00": {
            'trades': v['trades'],
            'win_rate': v['wins'] / v['trades'],
            'avg_pnl': v['total_pnl'] / v['trades']
        } for h, v in sorted(hours.items())}
    
    def _distribution_by_pnl(self, pnls: List[float]) -> Dict:
        """توزيع حسب نطاق الربح/الخسارة"""
        ranges = {
            'large_profit': len([p for p in pnls if p > 100]),
            'medium_profit': len([p for p in pnls if 50 < p <= 100]),
            'small_profit': len([p for p in pnls if 0 < p <= 50]),
            'breakeven': len([p for p in pnls if p == 0]),
            'small_loss': len([p for p in pnls if -50 <= p < 0]),
            'medium_loss': len([p for p in pnls if -100 <= p < -50]),
            'large_loss': len([p for p in pnls if p < -100])
        }
        return ranges
    
    def _max_consecutive(self, condition_func) -> int:
        """أقصى عدد متتالي"""
        max_count = 0
        current_count = 0
        
        for trade in sorted(self.trades, key=lambda x: x.entry_time):
            if condition_func(trade):
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    def _empty_summary(self) -> Dict:
        """ملخص فارغ"""
        return {
            'period_days': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0
        }
    
    def export_to_csv(self, filepath: str):
        """تصدير إلى CSV"""
        if not self.trades:
            return
        
        df = pd.DataFrame([
            {
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'symbol': t.symbol,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'volume': t.volume,
                'pnl': t.pnl,
                'holding_time': t.holding_time_minutes
            }
            for t in self.trades
        ])
        
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} trades to {filepath}")


# Singleton
performance_tracker = PerformanceTracker()
