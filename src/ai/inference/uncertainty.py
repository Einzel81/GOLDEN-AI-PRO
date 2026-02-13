"""
تقدير عدم اليقين
Uncertainty Estimation
"""

import numpy as np
from typing import Dict, List


class UncertaintyEstimator:
    """
    تقدير عدم اليقين في التنبؤات
    """
    
    def __init__(self, method: str = "mc_dropout"):
        self.method = method
    
    def estimate(
        self,
        model,
        X: np.ndarray,
        n_iterations: int = 100
    ) -> Dict:
        """
        تقدير عدم اليقين باستخدام Monte Carlo Dropout
        """
        predictions = []
        
        # تفعيل Dropout أثناء الاستدلال
        for _ in range(n_iterations):
            pred = model.predict(X)
            predictions.append(pred)
        
        predictions = np.array(predictions)
        
        # حساب الإحصائيات
        mean_pred = np.mean(predictions, axis=0)
        std_pred = np.std(predictions, axis=0)
        
        # فترة الثقة 95%
        confidence_lower = np.percentile(predictions, 2.5, axis=0)
        confidence_upper = np.percentile(predictions, 97.5, axis=0)
        
        return {
            'mean': mean_pred,
            'std': std_pred,
            'coefficient_of_variation': std_pred / (mean_pred + 1e-8),
            'confidence_interval': (confidence_lower, confidence_upper),
            'uncertainty_score': float(np.mean(std_pred))
        }
    
    def should_trade(self, uncertainty: Dict, threshold: float = 0.1) -> bool:
        """
        تحديد ما إذا كان يجب التداول بناءً على عدم اليقين
        """
        return uncertainty['uncertainty_score'] < threshold
