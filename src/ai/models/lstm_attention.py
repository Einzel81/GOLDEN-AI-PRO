"""
نموذج LSTM مع Attention Mechanism
LSTM with Attention for Time Series Prediction
"""

import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Input, LSTM, Dense, Dropout, Bidirectional,
    Attention, Concatenate, LayerNormalization, GlobalAveragePooling1D
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
import numpy as np
from typing import Tuple, Dict, Optional, List
from loguru import logger


class AttentionLayer(tf.keras.layers.Layer):
    """
    طبقة Attention مخصصة
    """
    def __init__(self, units):
        super(AttentionLayer, self).__init__()
        self.W1 = Dense(units)
        self.W2 = Dense(units)
        self.V = Dense(1)
        
    def call(self, query, values):
        # query: hidden state (batch_size, hidden_units)
        # values: all LSTM outputs (batch_size, time_steps, hidden_units)
        
        # Expand query dimensions to match values
        query_with_time_axis = tf.expand_dims(query, 1)
        
        # Calculate attention scores
        score = self.V(tf.nn.tanh(
            self.W1(query_with_time_axis) + self.W2(values)
        ))
        
        # Attention weights
        attention_weights = tf.nn.softmax(score, axis=1)
        
        # Context vector
        context_vector = attention_weights * values
        context_vector = tf.reduce_sum(context_vector, axis=1)
        
        return context_vector, attention_weights


class LSTMAttentionModel:
    """
    نموذج LSTM مع Attention للتنبؤ بأسعار الذهب
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        n_features: int = 20,
        lstm_units: List[int] = [128, 64],
        dropout_rate: float = 0.3,
        learning_rate: float = 0.001
    ):
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.model = None
        self.history = None
        
    def build_model(self) -> Model:
        """بناء النموذج"""
        
        # Input layer
        inputs = Input(shape=(self.sequence_length, self.n_features), name='input_layer')
        
        # First LSTM layer with return sequences for attention
        x = Bidirectional(
            LSTM(self.lstm_units[0], return_sequences=True, name='lstm_1')
        )(inputs)
        x = LayerNormalization()(x)
        x = Dropout(self.dropout_rate)(x)
        
        # Second LSTM layer
        x = Bidirectional(
            LSTM(self.lstm_units[1], return_sequences=True, name='lstm_2')
        )(x)
        x = LayerNormalization()(x)
        x = Dropout(self.dropout_rate)(x)
        
        # Attention mechanism
        # Use the last output as query
        query = LSTM(self.lstm_units[1], return_sequences=False)(x)
        
        # Apply attention
        attention_layer = AttentionLayer(self.lstm_units[1])
        context_vector, attention_weights = attention_layer(query, x)
        
        # Concatenate context with query
        combined = Concatenate()([context_vector, query])
        
        # Dense layers
        x = Dense(64, activation='relu')(combined)
        x = Dropout(self.dropout_rate / 2)(x)
        x = Dense(32, activation='relu')(x)
        
        # Output layer (3 outputs: direction, entry, confidence)
        direction = Dense(3, activation='softmax', name='direction')(x)  # Up, Down, Neutral
        entry_price = Dense(1, name='entry_price')(x)
        confidence = Dense(1, activation='sigmoid', name='confidence')(x)
        
        model = Model(
            inputs=inputs,
            outputs=[direction, entry_price, confidence],
            name='LSTM_Attention_Gold_Predictor'
        )
        
        # Compile
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss={
                'direction': 'categorical_crossentropy',
                'entry_price': 'mse',
                'confidence': 'binary_crossentropy'
            },
            loss_weights={
                'direction': 1.0,
                'entry_price': 0.5,
                'confidence': 0.3
            },
            metrics={
                'direction': 'accuracy',
                'entry_price': 'mae',
                'confidence': 'mae'
            }
        )
        
        self.model = model
        logger.info(f"Model built with {model.count_params()} parameters")
        return model
    
    def train(
        self,
        X_train: np.ndarray,
        y_direction: np.ndarray,
        y_entry: np.ndarray,
        y_confidence: np.ndarray,
        validation_split: float = 0.2,
        epochs: int = 100,
        batch_size: int = 32,
        callbacks: Optional[List] = None
    ) -> Dict:
        """تدريب النموذج"""
        
        if self.model is None:
            self.build_model()
        
        # Default callbacks
        if callbacks is None:
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=15,
                    restore_best_weights=True,
                    verbose=1
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-7,
                    verbose=1
                ),
                ModelCheckpoint(
                    'models/lstm_attention_best.h5',
                    monitor='val_direction_accuracy',
                    save_best_only=True,
                    verbose=1
                )
            ]
        
        # Train
        self.history = self.model.fit(
            X_train,
            {
                'direction': y_direction,
                'entry_price': y_entry,
                'confidence': y_confidence
            },
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return self.history.history
    
    def predict(self, X: np.ndarray) -> Dict:
        """التنبؤ"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        predictions = self.model.predict(X)
        
        return {
            'direction_prob': predictions[0],
            'entry_price': predictions[1],
            'confidence': predictions[2]
        }
    
    def save(self, path: str):
        """حفظ النموذج"""
        if self.model is None:
            raise ValueError("No model to save")
        self.model.save(path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str):
        """تحميل النموذج"""
        self.model = tf.keras.models.load_model(
            path,
            custom_objects={'AttentionLayer': AttentionLayer}
        )
        logger.info(f"Model loaded from {path}")
    
    def get_attention_weights(self, X: np.ndarray) -> np.ndarray:
        """استخراج أوزان الانتباه للتفسير"""
        # Create a model that outputs attention weights
        attention_model = Model(
            inputs=self.model.input,
            outputs=self.model.get_layer('attention_layer').output
        )
        _, weights = attention_model.predict(X)
        return weights
