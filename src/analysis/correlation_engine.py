"""
محرك تحليل الارتباطات بين الذهب والدولار والمعادن
يكشف التباعدات والإشارات المتقدمة
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DivergenceType(Enum):
    """أنواع التباعد"""
    NONE = "none"
    BULLISH = "bullish"      # تباعد صعودي: الذهب يرتفع والدولار يرتفع (نادر)
    BEARISH = "bearish"      # تباعد هبوطي: الذهب ينخفض والدولار ينخفض (نادر)
    HIDDEN_BULLISH = "hidden_bullish"  # تباعد خفي صعودي
    HIDDEN_BEARISH = "hidden_bearish"  # تباعد خفي هبوطي


@dataclass
class CorrelationSignal:
    """إشارة تحليل الارتباط"""
    correlation: float
    dxy_trend: str
    divergence: DivergenceType
    strength: float  # 0.0 إلى 1.0
    recommendation: str  # 'strong_buy', 'buy', 'neutral', 'sell', 'strong_sell'
    confidence_boost: float  # -0.2 إلى +0.2 لتعديل الثقة


class CorrelationAnalyzer:
    """
    محلل الارتباطات المتقدم بين الذهب والدولار
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.window_short = self.config.get('CORR_WINDOW_SHORT', 10)
        self.window_medium = self.config.get('CORR_WINDOW_MEDIUM', 20)
        self.window_long = self.config.get('CORR_WINDOW_LONG', 50)
        self.divergence_threshold = self.config.get('DIVERGENCE_THRESHOLD', 0.02)
        
    def calculate_rolling_correlation(self, 
                                      gold_prices: pd.Series, 
                                      dxy_prices: pd.Series,
                                      window: int = 20) -> pd.Series:
        """
        حساب الارتباط المتحرك بين الذهب والدولار
        """
        # محاذاة البيانات
        gold, dxy = gold_prices.align(dxy_prices, join='inner')
        
        # حساب التغيرات النسبية
        gold_returns = gold.pct_change()
        dxy_returns = dxy.pct_change()
        
        # الارتباط المتحرك
        correlation = gold_returns.rolling(window=window).corr(dxy_returns)
        
        return correlation
    
    def analyze_dxy_trend(self, dxy_data: pd.DataFrame) -> Dict:
        """
        تحليل اتجاه مؤشر الدولار
        """
        if dxy_data is None or dxy_data.empty:
            return {'trend': 'UNKNOWN', 'strength': 0.0}
        
        close = dxy_data['close']
        
        # حساب المتوسطات المتحركة
        ema_9 = close.ewm(span=9).mean()
        ema_21 = close.ewm(span=21).mean()
        ema_50 = close.ewm(span=50).mean()
        
        # آخر القيم
        last_close = close.iloc[-1]
        last_ema9 = ema_9.iloc[-1]
        last_ema21 = ema_21.iloc[-1]
        last_ema50 = ema_50.iloc[-1]
        
        # التغير خلال 5 فترات
        change_5 = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] if len(close) >= 6 else 0
        
        # تحديد الاتجاه
        if last_close > last_ema9 > last_ema21 > last_ema50 and change_5 > 0.005:
            trend = "STRONG_BULLISH"
            strength = 1.0
        elif last_close > last_ema21 and change_5 > 0.002:
            trend = "BULLISH"
            strength = 0.7
        elif last_close < last_ema9 < last_ema21 < last_ema50 and change_5 < -0.005:
            trend = "STRONG_BEARISH"
            strength = 1.0
        elif last_close < last_ema21 and change_5 < -0.002:
            trend = "BEARISH"
            strength = 0.7
        else:
            trend = "NEUTRAL"
            strength = 0.3
        
        return {
            'trend': trend,
            'strength': strength,
            'current_price': last_close,
            'change_5_periods': change_5,
            'above_ema50': last_close > last_ema50
        }
    
    def detect_divergence(self, 
                          gold_data: pd.DataFrame, 
                          dxy_data: pd.DataFrame,
                          lookback: int = 10) -> DivergenceType:
        """
        كشف التباعد بين الذهب والدولار (إشارة قوية جداً)
        """
        if gold_data is None or dxy_data is None:
            return DivergenceType.NONE
        
        # محاذاة البيانات
        gold, dxy = gold_data.align(dxy_data, join='inner')
        
        if len(gold) < lookback + 5:
            return DivergenceType.NONE
        
        # حساب التغيرات
        gold_change = (gold['close'].iloc[-1] - gold['close'].iloc[-lookback]) / gold['close'].iloc[-lookback]
        dxy_change = (dxy['close'].iloc[-1] - dxy['close'].iloc[-lookback]) / dxy['close'].iloc[-lookback]
        
        # تباعد صعودي: الذهب يرتفع بقوة والدولار يرتفع أيضاً (نادر - قوة شرائية هائلة)
        if gold_change > self.divergence_threshold and dxy_change > 0.01:
            logger.info(f"تباعد صعودي نادر! Gold: {gold_change:.2%}, DXY: {dxy_change:.2%}")
            return DivergenceType.BULLISH
        
        # تباعد هبوطي: الذهب ينخفض بقوة والدولار ينخفض أيضاً (نادر - قوة بيعية هائلة)
        elif gold_change < -self.divergence_threshold and dxy_change < -0.01:
            logger.info(f"تباعد هبوطي نادر! Gold: {gold_change:.2%}, DXY: {dxy_change:.2%}")
            return DivergenceType.BEARISH
        
        # تباعد خفي صعودي: الذهب يرتفع والدولار يرتفع بقوة (الذهب يقاوم)
        elif gold_change > 0 and dxy_change > 0.015:
            return DivergenceType.HIDDEN_BULLISH
        
        # تباعد خفي هبوطي: الذهب ينخفض والدولار ينخفض بقوة (الذهب ضعيف)
        elif gold_change < 0 and dxy_change < -0.015:
            return DivergenceType.HIDDEN_BEARISH
        
        return DivergenceType.NONE
    
    def calculate_leading_indicators(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """
        حساب المؤشرات القيادية للذهب
        """
        signals = {}
        
        # 1. الفضة كمؤشر قيادي (تسبق الذهب عادةً)
        if 'silver' in data and 'gold' in data:
            silver = data['silver']
            gold = data['gold']
            
            # محاذاة البيانات
            silver_aligned, gold_aligned = silver.align(gold, join='inner')
            
            # حساب الزخم
            silver_momentum = silver_aligned['close'].pct_change(5)
            gold_momentum = gold_aligned['close'].pct_change(5)
            
            # إذا كانت الفضة تتحرك قبل الذهب
            if len(silver_momentum) >= 6:
                silver_recent = silver_momentum.iloc[-1]
                gold_recent = gold_momentum.iloc[-1]
                
                if abs(silver_recent) > 0.02 and abs(gold_recent) < 0.01:
                    signals['silver_lead'] = {
                        'direction': 'UP' if silver_recent > 0 else 'DOWN',
                        'strength': abs(silver_recent),
                        'signal': 'silver_moving_first'
                    }
        
        # 2. نسبة الذهب/الفضة
        if 'gold' in data and 'silver' in data:
            gold_close = data['gold']['close'].iloc[-1]
            silver_close = data['silver']['close'].iloc[-1]
            ratio = gold_close / silver_close
            
            # المتوسط التاريخي حوالي 60-80
            if ratio > 90:
                signals['gold_silver_ratio'] = {
                    'value': ratio,
                    'signal': 'gold_overvalued',  # الذهب مبالغ فيه
                    'bias': 'bearish'
                }
            elif ratio < 50:
                signals['gold_silver_ratio'] = {
                    'value': ratio,
                    'signal': 'gold_undervalued',  # الذهب مقوم بأقل من قيمته
                    'bias': 'bullish'
                }
        
        # 3. البلاتين والبلاديوم (طلب صناعي)
        if 'platinum' in data and 'palladium' in data:
            plat_change = data['platinum']['close'].pct_change(5).iloc[-1]
            pall_change = data['palladium']['close'].pct_change(5).iloc[-1]
            
            if plat_change > 0.03 and pall_change > 0.03:
                signals['industrial_demand'] = 'strong'
            elif plat_change < -0.03 and pall_change < -0.03:
                signals['industrial_demand'] = 'weak'
        
        return signals
    
    def generate_correlation_signal(self,
                                     gold_data: pd.DataFrame,
                                     dxy_data: pd.DataFrame,
                                     silver_data: pd.DataFrame = None) -> CorrelationSignal:
        """
        توليد إشارة الارتباط الشاملة
        """
        # 1. حساب الارتباط
        correlation = self.calculate_rolling_correlation(
            gold_data['close'], dxy_data['close'], self.window_medium
        ).iloc[-1] if not gold_data.empty and not dxy_data.empty else -0.8
        
        # 2. تحليل اتجاه الدولار
        dxy_analysis = self.analyze_dxy_trend(dxy_data)
        
        # 3. كشف التباعد
        divergence = self.detect_divergence(gold_data, dxy_data)
        
        # 4. حساب القوة والتوصية
        strength = 0.5
        recommendation = 'neutral'
        confidence_boost = 0.0
        
        # منطق اتخاذ القرار
        if dxy_analysis['trend'] == 'STRONG_BEARISH':
            # دولار ضعيف جداً = إشارة شراء قوية للذهب
            if divergence == DivergenceType.BULLISH:
                recommendation = 'strong_buy'
                strength = 0.95
                confidence_boost = 0.20
            else:
                recommendation = 'buy'
                strength = 0.80
                confidence_boost = 0.15
                
        elif dxy_analysis['trend'] == 'BEARISH':
            recommendation = 'buy'
            strength = 0.70
            confidence_boost = 0.10
            
        elif dxy_analysis['trend'] == 'STRONG_BULLISH':
            # دولار قوي جداً = إشارة بيع قوية للذهب
            if divergence == DivergenceType.BEARISH:
                recommendation = 'strong_sell'
                strength = 0.95
                confidence_boost = -0.20
            else:
                recommendation = 'sell'
                strength = 0.80
                confidence_boost = -0.15
                
        elif dxy_analysis['trend'] == 'BULLISH':
            recommendation = 'sell'
            strength = 0.70
            confidence_boost = -0.10
        
        # تعديل بناءً على التباعد
        if divergence == DivergenceType.BULLISH:
            recommendation = 'strong_buy'
            confidence_boost = max(confidence_boost, 0.25)
        elif divergence == DivergenceType.BEARISH:
            recommendation = 'strong_sell'
            confidence_boost = min(confidence_boost, -0.25)
        
        return CorrelationSignal(
            correlation=correlation,
            dxy_trend=dxy_analysis['trend'],
            divergence=divergence,
            strength=strength,
            recommendation=recommendation,
            confidence_boost=confidence_boost
        )
    
    def get_market_context_summary(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """
        ملخص السياق السوقي الكامل
        """
        if 'gold' not in data or 'dollar_index' not in data:
            return {'error': 'بيانات غير كافية'}
        
        gold = data['gold']
        dxy = data['dollar_index']
        silver = data.get('silver')
        
        # الإشارة الرئيسية
        signal = self.generate_correlation_signal(gold, dxy, silver)
        
        # المؤشرات القيادية
        leading = self.calculate_leading_indicators(data)
        
        # الارتباطات متعددة الفترات
        corr_short = self.calculate_rolling_correlation(
            gold['close'], dxy['close'], self.window_short
        ).iloc[-1]
        corr_long = self.calculate_rolling_correlation(
            gold['close'], dxy['close'], self.window_long
        ).iloc[-1]
        
        return {
            'primary_signal': signal,
            'leading_indicators': leading,
            'correlations': {
                'short_term': corr_short,
                'medium_term': signal.correlation,
                'long_term': corr_long
            },
            'dxy_analysis': self.analyze_dxy_trend(dxy),
            'timestamp': pd.Timestamp.now()
        }
