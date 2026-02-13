"""
نموذج Transformer للسلاسل الزمنية
Time Series Transformer Model
"""

import tensorflow as tf
from tensorflow.keras import layers, Model


class TimeSeriesTransformer:
    """
    Transformer architecture adapted for time series forecasting
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        n_features: int = 20,
        d_model: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1
    ):
        self.seq_len = sequence_length
        self.n_features = n_features
        self.d_model = d_model
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.dropout = dropout
        self.model = None
        
    def build_model(self) -> Model:
        """بناء نموذج Transformer"""
        
        inputs = layers.Input(shape=(self.seq_len, self.n_features))
        
        # Linear projection to d_model
        x = layers.Dense(self.d_model)(inputs)
        
        # Positional encoding
        positions = tf.range(start=0, limit=self.seq_len, delta=1)
        pos_encoding = self._positional_encoding(self.seq_len, self.d_model)
        x = x + pos_encoding
        
        # Transformer blocks
        for _ in range(self.num_layers):
            x = self._transformer_block(x)
        
        # Global average pooling
        x = layers.GlobalAveragePooling1D()(x)
        
        # Output layers
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(self.dropout)(x)
        
        # Multi-task outputs
        direction = layers.Dense(3, activation='softmax', name='direction')(x)
        price = layers.Dense(1, name='price')(x)
        
        self.model = Model(inputs=inputs, outputs=[direction, price])
        
        self.model.compile(
            optimizer='adam',
            loss={
                'direction': 'categorical_crossentropy',
                'price': 'mse'
            },
            metrics={'direction': 'accuracy'}
        )
        
        return self.model
    
    def _positional_encoding(self, position: int, d_model: int) -> tf.Tensor:
        """ترميز الموضع"""
        angles = self._get_angles(
            np.arange(position)[:, np.newaxis],
            np.arange(d_model)[np.newaxis, :],
            d_model
        )
        
        angles[:, 0::2] = np.sin(angles[:, 0::2])
        angles[:, 1::2] = np.cos(angles[:, 1::2])
        
        return tf.cast(angles[np.newaxis, ...], dtype=tf.float32)
    
    def _get_angles(self, pos, i, d_model):
        """حساب الزوايا للترميز الموضعي"""
        angle_rates = 1 / np.power(10000, (2 * (i // 2)) / np.float32(d_model))
        return pos * angle_rates
    
    def _transformer_block(self, x):
        """كتلة Transformer"""
        # Multi-head attention
        attn_output = layers.MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=self.d_model
        )(x, x)
        attn_output = layers.Dropout(self.dropout)(attn_output)
        out1 = layers.LayerNormalization(epsilon=1e-6)(x + attn_output)
        
        # Feed forward
        ff_output = layers.Dense(self.d_model * 4, activation='relu')(out1)
        ff_output = layers.Dense(self.d_model)(ff_output)
        ff_output = layers.Dropout(self.dropout)(ff_output)
        
        return layers.LayerNormalization(epsilon=1e-6)(out1 + ff_output)
