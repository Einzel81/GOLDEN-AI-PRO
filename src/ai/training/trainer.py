"""
مدرب النماذج
Model Trainer
"""

import numpy as np
from typing import Dict, Optional, Callable
from loguru import logger


class ModelTrainer:
    """
    مدرب موحد للنماذج
    """
    
    def __init__(
        self,
        model,
        batch_size: int = 32,
        epochs: int = 100,
        validation_split: float = 0.2
    ):
        self.model = model
        self.batch_size = batch_size
        self.epochs = epochs
        self.validation_split = validation_split
        self.history = None
        
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        callbacks: Optional[list] = None
    ) -> Dict:
        """تدريب النموذج"""
        
        logger.info(f"Starting training: {X_train.shape[0]} samples")
        
        validation_data = (X_val, y_val) if X_val is not None else None
        
        self.history = self.model.fit(
            X_train, y_train,
            batch_size=self.batch_size,
            epochs=self.epochs,
            validation_split=self.validation_split if validation_data is None else 0,
            validation_data=validation_data,
            callbacks=callbacks or [],
            verbose=1
        )
        
        logger.info("Training completed")
        
        return self.history.history
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """تقييم النموذج"""
        results = self.model.evaluate(X_test, y_test, verbose=0)
        return dict(zip(self.model.metrics_names, results))
    
    def save_checkpoint(self, path: str):
        """حفظ checkpoint"""
        self.model.save(path)
        logger.info(f"Checkpoint saved: {path}")
