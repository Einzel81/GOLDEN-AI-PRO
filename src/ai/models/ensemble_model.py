"""
نموذج المجموعة
Ensemble Model combining multiple algorithms
"""

import numpy as np
from typing import Dict, List, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
import xgboost as xgb
import lightgbm as lgb
from loguru import logger


class EnsembleModel:
    """
    مجموعة من النماذج: XGBoost + LightGBM + Random Forest
    """
    
    def __init__(self):
        self.models: Dict[str, any] = {}
        self.weights = {
            'xgboost': 0.4,
            'lightgbm': 0.4,
            'random_forest': 0.2
        }
        
    def fit(self, X: np.ndarray, y: np.ndarray):
        """تدريب جميع النماذج"""
        
        # XGBoost
        logger.info("Training XGBoost...")
        self.models['xgboost'] = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
        self.models['xgboost'].fit(X, y)
        
        # LightGBM
        logger.info("Training LightGBM...")
        self.models['lightgbm'] = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
        self.models['lightgbm'].fit(X, y)
        
        # Random Forest
        logger.info("Training Random Forest...")
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=100,
            max_depth=10
        )
        self.models['random_forest'].fit(X, y)
        
        logger.info("Ensemble training complete")
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """التنبؤ بالاحتمالات الموزونة"""
        probabilities = np.zeros((X.shape[0], 3))  # 3 classes
        
        for name, model in self.models.items():
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X)
                probabilities += self.weights[name] * proba
        
        return probabilities
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """التنبؤ بالفئة"""
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)
    
    def get_feature_importance(self, feature_names: List[str]) -> Dict[str, float]:
        """أهمية الميزات المجمعة"""
        importances = {}
        
        for name, model in self.models.items():
            if hasattr(model, 'feature_importances_'):
                for feat, imp in zip(feature_names, model.feature_importances_):
                    if feat not in importances:
                        importances[feat] = []
                    importances[feat].append(imp * self.weights[name])
        
        # المتوسط الموزون
        return {
            feat: np.mean(imps) 
            for feat, imps in importances.items()
        }
