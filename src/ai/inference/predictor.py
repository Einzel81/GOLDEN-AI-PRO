"""
نظام التنبؤ
Prediction System
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
import tensorflow as tf
from loguru import logger

from src.ai.models.lstm_attention import LSTMAttentionModel


class Predictor:
    """
    نظام التنبؤ الموحد
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.models: Dict[str, any] = {}
        self.scaler = None
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, path: str, name: str = "default"):
        """تحميل نموذج"""
        try:
            model = LSTMAttentionModel()
            model.load(path)
            self.models[name] = model
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
    
    def predict(self, data: np.ndarray, model_name: str = "default") -> Dict:
        """التنبؤ باستخدام نموذج محدد"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        model = self.models[model_name]
        predictions = model.predict(data)
        
        # تحليل النتائج
        direction_probs = predictions['direction_prob'][0]
        direction = np.argmax(direction_probs)
        
        return {
            'direction': ['down', 'neutral', 'up'][direction],
            'direction_confidence': float(direction_probs[direction]),
            'entry_price': float(predictions['entry_price'][0][0]),
            'confidence': float(predictions['confidence'][0][0]),
            'probabilities': {
                'down': float(direction_probs[0]),
                'neutral': float(direction_probs[1]),
                'up': float(direction_probs[2])
            }
        }
    
    def ensemble_predict(self, data: np.ndarray) -> Dict:
        """تنبؤ باستخدام مجموعة نماذج"""
        if len(self.models) == 0:
            raise ValueError("No models loaded")
        
        predictions = []
        for name, model in self.models.items():
            try:
                pred = self.predict(data, name)
                predictions.append(pred)
            except Exception as e:
                logger.error(f"Prediction failed for {name}: {e}")
        
        if not predictions:
            return {'direction': 'neutral', 'confidence': 0}
        
        # دمج التنبؤات
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        
        # التصويت على الاتجاه
        directions = [p['direction'] for p in predictions]
        direction = max(set(directions), key=directions.count)
        
        return {
            'direction': direction,
            'confidence': float(avg_confidence),
            'models_used': len(predictions),
            'individual_predictions': predictions
        }
