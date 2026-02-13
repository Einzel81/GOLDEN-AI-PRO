"""
التحقق المتقاطع الزمني
Time Series Cross-Validation
"""

import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from typing import List, Dict, Callable


class TimeSeriesCrossValidator:
    """
    تحقق متقاطع للسلاسل الزمنية
    """
    
    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits
        self.tscv = TimeSeriesSplit(n_splits=n_splits)
        
    def cross_validate(
        self,
        model_builder: Callable,
        X: np.ndarray,
        y: np.ndarray,
        fit_params: Dict = None
    ) -> Dict:
        """التحقق المتقاطع"""
        
        scores = []
        fold_results = []
        
        for fold, (train_idx, val_idx) in enumerate(self.tscv.split(X)):
            print(f"Fold {fold + 1}/{self.n_splits}")
            
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # بناء نموذج جديد لكل fold
            model = model_builder()
            
            # التدريب
            model.fit(X_train, y_train, **(fit_params or {}))
            
            # التقييم
            score = model.evaluate(X_val, y_val, verbose=0)
            scores.append(score)
            
            fold_results.append({
                'fold': fold + 1,
                'train_size': len(train_idx),
                'val_size': len(val_idx),
                'score': score
            })
        
        return {
            'mean_score': np.mean(scores),
            'std_score': np.std(scores),
            'fold_results': fold_results
        }
