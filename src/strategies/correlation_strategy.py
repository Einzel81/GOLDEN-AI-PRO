"""
استراتيجية التداول المبنية على الارتباطات
تدمج إشارات الذهب الأساسية مع تحليل DXY
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
import logging

from ..analysis.correlation_engine import CorrelationAnalyzer, CorrelationSignal
from ..analysis.smc_analyzer import SMCAnalyzer  # افتراضياً موجود في المشروع

logger = logging.getLogger(__name__)


@dataclass
class TradingDecision:
    قرار التداول النهائي
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 إلى 1.0
    position_size_multiplier: float  # مضاعف حجم المركز
    stop_loss_adjustment: float  # تعديل وقف الخسارة
    take_profit_adjustment: float  # تعديل جني الأرباح
    reasoning: str  # سبب القرار


class DXYCorrelationStrategy:
    """
    استراتيجية الارتباط مع الدولار
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.correlation_analyzer = CorrelationAnalyzer(config)
        self.min_confidence = self.config.get('MIN_CONFIDENCE', 0.65)
        self.max_correlation_boost = self.config.get('MAX_CORRELATION_BOOST', 0.20)
        
    def combine_signals(self,
                        gold_signal: Dict,
                        correlation_signal: CorrelationSignal,
                        smc_signal: Optional[Dict] = None) -> TradingDecision:
        """
        دمج إشارات متعددة لاتخاذ القرار النهائي
        """
        # الثقة الأساسية من إشارة الذهب
        base_confidence = gold_signal.get('confidence', 0.5)
        base_action = gold_signal.get('action', 'HOLD')
        
        # تعديل الثقة بناءً على DXY
        adjusted_confidence = base_confidence + correlation_signal.confidence_boost
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        # منطق الدمج
        action = base_action
        size_multiplier = 1.0
        sl_adjustment = 0.0
        tp_adjustment = 0.0
        reasoning_parts = []
        
        # 1. تأثير DXY على الإشارة
        if correlation_signal.recommendation in ['strong_buy', 'buy']:
            if base_action == 'BUY':
                # تأكيد قوي - زيادة الحجم
                action = 'BUY'
                size_multiplier = 1.3
                tp_adjustment = 0.05  # زيادة الهدف 5%
                reasoning_parts.append(f"DXY ضعيف ({correlation_signal.dxy_trend}) يؤكد شراء الذهب")
                
            elif base_action == 'SELL':
                # تعارض - تقليل الثقة أو الامتناع
                if adjusted_confidence < self.min_confidence:
                    action = 'HOLD'
                    reasoning_parts.append("تعارض: DXY ضعيف لكن إشارة الذهب بيع - الامتناع")
                else:
                    action = 'SELL'
                    size_multiplier = 0.5
                    sl_adjustment = 0.02  # توسيع الوقف
                    reasoning_parts.append("تعارض: DXY ضعيف يضعف إشارة البيع")
                    
        elif correlation_signal.recommendation in ['strong_sell', 'sell']:
            if base_action == 'SELL':
                # تأكيد قوي - زيادة الحجم
                action = 'SELL'
                size_multiplier = 1.3
                tp_adjustment = 0.05
                reasoning_parts.append(f"DXY قوي ({correlation_signal.dxy_trend}) يؤكد بيع الذهب")
                
            elif base_action == 'BUY':
                # تعارض
                if adjusted_confidence < self.min_confidence:
                    action = 'HOLD'
                    reasoning_parts.append("تعارض: DXY قوي لكن إشارة الذهب شراء - الامتناع")
                else:
                    action = 'BUY'
                    size_multiplier = 0.5
                    sl_adjustment = 0.02
                    reasoning_parts.append("تعارض: DXY قوي يضعف إشارة الشراء")
        
        # 2. تأثير التباعد النادر (قوة فائقة)
        if correlation_signal.divergence.value != 'none':
            if 'BULLISH' in correlation_signal.divergence.value:
                if base_action == 'BUY':
                    size_multiplier = 1.5
                    reasoning_parts.append("تباعد صعودي نادر - فرصة استثنائية!")
            elif 'BEARISH' in correlation_signal.divergence.value:
                if base_action == 'SELL':
                    size_multiplier = 1.5
                    reasoning_parts.append("تباعد هبوطي نادر - فرصة استثنائية!")
        
        # 3. دمج SMC إذا توفر
        if smc_signal:
            smc_bias = smc_signal.get('bias', 'neutral')
            if smc_bias == 'bullish' and action == 'BUY':
                adjusted_confidence += 0.05
                reasoning_parts.append("SMC يؤكد الاتجاه الصعودي")
            elif smc_bias == 'bearish' and action == 'SELL':
                adjusted_confidence += 0.05
                reasoning_parts.append("SMC يؤكد الاتجاه الهبوطي")
        
        # 4. تعديل وقف الخسارة بناءً على قوة DXY
        if correlation_signal.strength > 0.8:
            sl_adjustment += 0.01  # وقف أضيق عند الثقة العالية
        
        return TradingDecision(
            action=action,
            confidence=round(adjusted_confidence, 2),
            position_size_multiplier=round(size_multiplier, 2),
            stop_loss_adjustment=round(sl_adjustment, 4),
            take_profit_adjustment=round(tp_adjustment, 4),
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else "قرار بناءً على إشارة الذهب فقط"
        )
    
    def should_filter_trade(self, 
                           gold_signal: Dict,
                           correlation_context: Dict) -> bool:
        """
        فلترة الصفقات بناءً على السياق
        """
        dxy_trend = correlation_context.get('dxy_analysis', {}).get('trend', 'NEUTRAL')
        correlation = correlation_context.get('correlations', {}).get('medium_term', -0.8)
        
        # فلتر 1: لا تتداول ضد الدولار القوي جداً
        if dxy_trend == 'STRONG_BULLISH' and gold_signal.get('action') == 'BUY':
            if gold_signal.get('confidence', 0) < 0.75:
                logger.warning("رفض صفقة شراء: الدولار قوي جداً وثقة منخفضة")
                return True
        
        # فلتر 2: لا تتداول ضد الدولار الضعيف جداً
        if dxy_trend == 'STRONG_BEARISH' and gold_signal.get('action') == 'SELL':
            if gold_signal.get('confidence', 0) < 0.75:
                logger.warning("رفض صفقة بيع: الدولار ضعيف جداً وثقة منخفضة")
                return True
        
        # فلتر 3: الارتباط ضعيف جداً (تغير في السلوك)
        if abs(correlation) < 0.3:
            logger.warning("الارتباط ضعيف جداً - السوق غير طبيعي")
            return True
        
        return False
    
    def get_position_size_adjustment(self, 
                                      volatility: float,
                                      correlation_strength: float) -> float:
        """
        تعديل حجم المركز بناءً على التقلب والارتباط
        """
        base_size = 1.0
        
        # تقليل الحجم عند التقلب العالي
        if volatility > 0.02:  # 2% تقلب يومي
            base_size *= 0.7
        
        # زيادة الحجم عند قوة الارتباط العالية
        if correlation_strength > 0.85:
            base_size *= 1.2
        
        return base_size
