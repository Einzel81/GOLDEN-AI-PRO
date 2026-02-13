"""
ضبط المعاملات الفائقة
Hyperparameter Tuning with Optuna
"""

import optuna
from typing import Dict, Any, Callable
from loguru import logger


class HyperparameterTuner:
    """
    ضبط المعاملات باستخدام Optuna
    """
    
    def __init__(
        self,
        model_builder: Callable,
        X_train: Any,
        y_train: Any,
        X_val: Any,
        y_val: Any,
        n_trials: int = 100
    ):
        self.model_builder = model_builder
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.n_trials = n_trials
        self.study = None
        
    def objective(self, trial: optuna.Trial) -> float:
        """دالة الهدف للتحسين"""
        
        # اقتراح المعاملات
        params = {
            'lstm_units_1': trial.suggest_int('lstm_units_1', 32, 256),
            'lstm_units_2': trial.suggest_int('lstm_units_2', 16, 128),
            'dropout': trial.suggest_float('dropout', 0.1, 0.5),
            'learning_rate': trial.suggest_float('learning_rate', 1e-5, 1e-2, log=True),
            'batch_size': trial.suggest_categorical('batch_size', [16, 32, 64, 128])
        }
        
        # بناء وتدريب النموذج
        model = self.model_builder(params)
        
        # تدريب سريع للتقييم
        history = model.fit(
            self.X_train, self.y_train,
            batch_size=params['batch_size'],
            epochs=20,
            validation_split=0.2,
            verbose=0
        )
        
        # إرجاع الدقة التحقق (للتعظيم)
        val_accuracy = max(history.history.get('val_accuracy', [0]))
        return val_accuracy
    
    def tune(self) -> Dict[str, Any]:
        """بدء الضبط"""
        logger.info(f"Starting hyperparameter tuning with {self.n_trials} trials...")
        
        self.study = optuna.create_study(direction='maximize')
        self.study.optimize(self.objective, n_trials=self.n_trials, show_progress_bar=True)
        
        best_params = self.study.best_params
        best_value = self.study.best_value
        
        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Best validation accuracy: {best_value:.4f}")
        
        return {
            'best_params': best_params,
            'best_value': best_value,
            'n_trials': self.n_trials
        }
    
    def get_optimization_history(self):
        """الحصول على تاريخ التحسين"""
        if self.study is None:
            return []
        return self.study.trials_dataframe()
