"""
محرك دمج الإشارات (Fusion Engine)
Multi-signal fusion with confidence weighting
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

from config.settings import settings


@dataclass
class SignalInput:
    """مدخل إشارة"""
    source: str  # 'smc', 'lstm', 'transformer', 'sentiment', etc.
    signal: str  # 'buy', 'sell', 'neutral'
    confidence: float  # 0.0 to 1.0
    weight: float  # Dynamic weight based on historical performance
    metadata: Dict = None


class FusionEngine:
    """
    محرك دمج متقدم يجمع:
    - إشارات SMC
    - تنبؤات LSTM/Transformer
    - تحليل المشاعر
    - بيانات السوق الخارجية
    """
    
    def __init__(self):
        self.source_weights = settings.ENSEMBLE_WEIGHTS.copy()
        self.performance_history = {source: [] for source in self.source_weights.keys()}
        self.min_confidence_threshold = settings.CONFIDENCE_THRESHOLD
        
    def fuse(self, signals: List[SignalInput], market_context: Dict) -> Dict:
        """
        دمج الإشارات وإنتاج قرار نهائي
        """
        if not signals:
            return {
                'final_signal': 'neutral',
                'confidence': 0.0,
                'direction_score': 0.0,
                'components': [],
                'reasoning': 'No signals provided'
            }
        
        # حساب الأوزان الديناميكية
        dynamic_weights = self._calculate_dynamic_weights(signals)
        
        # حساب درجة الاتجاه
        direction_score = 0.0
        total_weight = 0.0
        buy_confidence = 0.0
        sell_confidence = 0.0
        
        component_details = []
        
        for signal in signals:
            weight = dynamic_weights.get(signal.source, 0.25)
            
            # حساب المساهمة في الاتجاه
            if signal.signal == 'buy':
                contribution = signal.confidence * weight
                direction_score += contribution
                buy_confidence += contribution
            elif signal.signal == 'sell':
                contribution = -signal.confidence * weight
                direction_score += contribution
                sell_confidence += abs(contribution)
            
            total_weight += weight
            
            component_details.append({
                'source': signal.source,
                'signal': signal.signal,
                'raw_confidence': signal.confidence,
                'weight': weight,
                'contribution': contribution if signal.signal != 'neutral' else 0
            })
        
        # Normalization
        if total_weight > 0:
            direction_score /= total_weight
        
        # تحديد الإشارة النهائية
        final_signal, final_confidence = self._determine_final_signal(
            direction_score, buy_confidence, sell_confidence, total_weight
        )
        
        # التحقق من سياق السوق
        market_alignment = self._check_market_alignment(final_signal, market_context)
        
        # تعديل الثقة بناءً على السياق
        final_confidence *= market_alignment
        
        return {
            'final_signal': final_signal,
            'confidence': round(final_confidence, 3),
            'direction_score': round(direction_score, 3),
            'components': component_details,
            'market_alignment': market_alignment,
            'reasoning': self._generate_reasoning(final_signal, component_details, market_context),
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _calculate_dynamic_weights(self, signals: List[SignalInput]) -> Dict[str, float]:
        """حساب الأوزان الديناميكية بناءً على الأداء التاريخي"""
        weights = self.source_weights.copy()
        
        # تعديل الأوزان بناءً على الأداء الأخير
        for source in weights.keys():
            if source in self.performance_history and len(self.performance_history[source]) > 10:
                recent_accuracy = np.mean(self.performance_history[source][-10:])
                # رفع وزن المصادر الأكثر دقة
                weights[source] *= (0.8 + 0.4 * recent_accuracy)
        
        # Normalization
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}
    
    def _determine_final_signal(
        self,
        direction_score: float,
        buy_confidence: float,
        sell_confidence: float,
        total_weight: float
    ) -> tuple:
        """تحديد الإشارة النهائية"""
        
        threshold = 0.2  # حد الأهمية
        
        if direction_score > threshold and buy_confidence > self.min_confidence_threshold:
            confidence = min(buy_confidence / total_weight, 1.0)
            return 'buy', confidence
        elif direction_score < -threshold and sell_confidence > self.min_confidence_threshold:
            confidence = min(sell_confidence / total_weight, 1.0)
            return 'sell', confidence
        else:
            # حساب الثقة المحايدة
            neutral_confidence = 1.0 - max(buy_confidence, sell_confidence) / total_weight
            return 'neutral', max(0, neutral_confidence)
    
    def _check_market_alignment(self, signal: str, market_context: Dict) -> float:
        """التحقق من توافق الإشارة مع سياق السوق"""
        alignment = 1.0
        
        # التحقق من الاتجاه العام
        trend = market_context.get('trend', 'neutral')
        if signal == 'buy' and trend == 'bullish':
            alignment *= 1.1
        elif signal == 'sell' and trend == 'bearish':
            alignment *= 1.1
        elif signal != 'neutral' and trend != 'neutral' and signal != trend:
            alignment *= 0.7  # تناقض مع الاتجاه العام
        
        # التحقق من التقلب
        volatility = market_context.get('volatility', 0.5)
        if volatility > 0.8:  # تقلب عالي جداً
            alignment *= 0.8
        elif volatility < 0.2:  # تقلب منخفض (سوق راكد)
            alignment *= 0.9
        
        # التحقق من الأخبار الهامة
        high_impact_news = market_context.get('high_impact_news', False)
        if high_impact_news:
            alignment *= 0.7  # تقليل الثقة أثناء الأخبار
        
        return min(alignment, 1.0)
    
    def _generate_reasoning(
        self,
        final_signal: str,
        components: List[Dict],
        market_context: Dict
    ) -> str:
        """توليد تفسير للقرار"""
        reasoning_parts = []
        
        # ترتيب المكونات حسب الأهمية
        sorted_components = sorted(components, key=lambda x: abs(x['contribution']), reverse=True)
        
        top_contributors = [c for c in sorted_components[:3] if abs(c['contribution']) > 0.1]
        
        if final_signal == 'neutral':
            reasoning_parts.append("إشارة محايدة بسبب:")
            if not top_contributors:
                reasoning_parts.append("- ضعف الإشارات المكونة")
            else:
                for comp in top_contributors:
                    reasoning_parts.append(f"- {comp['source']}: {comp['signal']} (ضعيف)")
        else:
            reasoning_parts.append(f"إشارة {final_signal} قوية:")
            for comp in top_contributors:
                direction = "مع" if comp['contribution'] > 0 else "ضد"
                reasoning_parts.append(f"- {comp['source']}: {comp['signal']} ({comp['confidence']:.0%} ثقة)")
        
        # إضافة ملاحظات السياق
        if market_context.get('high_impact_news'):
            reasoning_parts.append("- تحذير: أخبار عالية التأثير قريباً")
        
        return " | ".join(reasoning_parts)
    
    def update_performance(self, source: str, was_correct: bool):
        """تحديث سجل أداء المصدر"""
        if source in self.performance_history:
            self.performance_history[source].append(1.0 if was_correct else 0.0)
            # الاحتفاظ بآخر 100 نتيجة فقط
            self.performance_history[source] = self.performance_history[source][-100:]
    
    def get_source_performance(self) -> Dict[str, float]:
        """الحصول على أداء المصادر"""
        performance = {}
        for source, history in self.performance_history.items():
            if history:
                performance[source] = np.mean(history)
        return performance
