"""
معيار كيلي (Kelly Criterion)
Optimal position sizing using Kelly Criterion
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class KellyResult:
    """نتيجة حساب كيلي"""
    kelly_fraction: float
    half_kelly: float
    quarter_kelly: float
    recommended_fraction: float
    expected_growth: float
    confidence: float


class KellyCriterion:
    """
    حاسب معيار كيلي للتحجيم الأمثل
    """
    
    def __init__(self, max_fraction: float = 0.25):
        self.max_fraction = max_fraction  # الحد الأقصى 25% لأسباب أمان
        
    def calculate(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        use_half_kelly: bool = True
    ) -> KellyResult:
        """
        حساب معيار كيلي
        
        المعادلة: f* = (p*b - q) / b
        حيث:
        - p: نسبة الربح (win rate)
        - q: نسبة الخسارة (1 - p)
        - b: نسبة متوسط الربح إلى متوسط الخسارة (avg_win / avg_loss)
        """
        
        if avg_loss == 0:
            logger.warning("Average loss is zero, cannot calculate Kelly")
            return KellyResult(0, 0, 0, 0, 0, 0)
        
        # حساب نسبة الربح إلى الخسارة
        win_loss_ratio = avg_win / avg_loss
        
        # حساب معيار كيلي الكامل
        q = 1 - win_rate
        kelly = (win_rate * win_loss_ratio - q) / win_loss_ratio
        
        # التأكد من أن القيمة موجبة (إلا إذا كانت الاستراتيجية خاسرة)
        kelly = max(0, kelly)
        
        # الحد الأقصى للأمان
        kelly = min(kelly, self.max_fraction)
        
        # النسخ الأكثر تحفظاً
        half_kelly = kelly * 0.5
        quarter_kelly = kelly * 0.25
        
        # التوصية النهائية
        recommended = half_kelly if use_half_kelly else kelly
        
        # حساب النمو المتوقع
        expected_growth = self._calculate_expected_growth(
            win_rate, win_loss_ratio, recommended
        )
        
        # حساب الثقة بناءً على حجم العينة
        confidence = self._calculate_confidence(win_rate, 100)  # افتراض 100 صفقة
        
        return KellyResult(
            kelly_fraction=kelly,
            half_kelly=half_kelly,
            quarter_kelly=quarter_kelly,
            recommended_fraction=recommended,
            expected_growth=expected_growth,
            confidence=confidence
        )
    
    def calculate_from_trades(self, trades: List[Dict], use_half_kelly: bool = True) -> KellyResult:
        """
        حساب كيلي من سجل الصفقات
        """
        if not trades or len(trades) < 10:
            logger.warning("Insufficient trades for Kelly calculation")
            return KellyResult(0, 0, 0, 0, 0, 0)
        
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
        
        win_rate = len(winning_trades) / len(trades)
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = abs(np.mean([t['pnl'] for t in losing_trades])) if losing_trades else 0
        
        return self.calculate(win_rate, avg_win, avg_loss, use_half_kelly)
    
    def _calculate_expected_growth(
        self,
        win_rate: float,
        win_loss_ratio: float,
        fraction: float
    ) -> float:
        """
        حساب النمو المتوقع للمحفظة
        """
        if win_loss_ratio <= 0:
            return 0
        
        # المعادلة: G = p * ln(1 + b*f) + q * ln(1 - f)
        q = 1 - win_rate
        b = win_loss_ratio
        
        growth = (
            win_rate * np.log(1 + b * fraction) +
            q * np.log(1 - fraction)
        )
        
        return np.exp(growth) - 1  # تحويل إلى نسبة مئوية
    
    def _calculate_confidence(self, win_rate: float, sample_size: int) -> float:
        """
        حساب فترة الثقة لنسبة الربح
        """
        if sample_size < 30:
            return 0.5  # ثقة منخفضة للعينات الصغيرة
        
        # حساب الخطأ المعياري
        se = np.sqrt((win_rate * (1 - win_rate)) / sample_size)
        
        # فترة الثقة 95%
        margin = 1.96 * se
        
        # الثقة تتناسب عكسياً مع عرض الفترة
        confidence = 1 - (margin / win_rate) if win_rate > 0 else 0
        
        return max(0, min(confidence, 1))
    
    def simulate_growth(
        self,
        initial_capital: float,
        kelly_fraction: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        n_trades: int = 100
    ) -> List[float]:
        """
        محاكاة نمو المحفظة
        """
        capital = initial_capital
        growth = [capital]
        
        for _ in range(n_trades):
            if np.random.random() < win_rate:
                # صفقة رابحة
                capital += capital * kelly_fraction * (avg_win / avg_loss)
            else:
                # صفقة خاسرة
                capital -= capital * kelly_fraction
            
            growth.append(capital)
        
        return growth
    
    def get_position_size(
        self,
        account_balance: float,
        kelly_fraction: float,
        stop_loss_pips: float,
        pip_value: float = 10.0
    ) -> Dict:
        """
        حساب حجم المركز بناءً على كيلي
        """
        risk_amount = account_balance * kelly_fraction
        
        # حساب حجم اللوت
        # XAUUSD: 1 lot = $10 per pip (تقريبي)
        lots = risk_amount / (stop_loss_pips * pip_value)
        
        return {
            'lots': round(lots, 2),
            'risk_amount': risk_amount,
            'risk_percent': kelly_fraction * 100,
            'stop_loss_pips': stop_loss_pips,
            'units': lots * 100  # 1 lot = 100 ounces
        }


# Helper function
def quick_kelly(
    wins: int,
    losses: int,
    total_profit: float,
    total_loss: float
) -> float:
    """
    حساب سريع لكيلي
    """
    total_trades = wins + losses
    if total_trades == 0 or total_loss == 0:
        return 0
    
    win_rate = wins / total_trades
    avg_win = total_profit / wins if wins > 0 else 0
    avg_loss = abs(total_loss) / losses if losses > 0 else 0
    
    kelly = KellyCriterion()
    result = kelly.calculate(win_rate, avg_win, avg_loss)
    
    return result.recommended_fraction
