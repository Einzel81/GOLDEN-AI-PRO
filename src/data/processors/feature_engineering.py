"""
هندسة الميزات المتقدمة
Advanced Feature Engineering for ML Models
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from scipy import stats
from sklearn.preprocessing import StandardScaler


class FeatureEngineer:
    """
    مهندس ميزات متقدم يقوم بإنشاء:
    - مؤشرات فنية تقليدية
    - ميزات SMC المخصصة
    - ميزات إحصائية
    - ميزات السلاسل الزمنية
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        إنشاء جميع الميزات
        """
        data = df.copy()
        
        # ميزات الأسعار الأساسية
        data = self._add_price_features(data)
        
        # المؤشرات الفنية
        data = self._add_technical_indicators(data)
        
        # ميزات الحجم
        data = self._add_volume_features(data)
        
        # ميزات إحصائية
        data = self._add_statistical_features(data)
        
        # ميزات السلاسل الزمنية
        data = self._add_time_series_features(data)
        
        # ميزات السلاسل الزمنية المتقدمة (Lagged)
        data = self._add_lagged_features(data)
        
        # إزالة القيم NaN
        data = data.dropna()
        
        return data
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ميزات الأسعار"""
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # المدى
        df['range'] = df['high'] - df['low']
        df['body'] = abs(df['close'] - df['open'])
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        
        # نسبة الجسم إلى المدى
        df['body_to_range'] = df['body'] / df['range']
        
        # اتجاه الشمعة
        df['candle_direction'] = np.where(df['close'] > df['open'], 1, 
                                         np.where(df['close'] < df['open'], -1, 0))
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """المؤشرات الفنية"""
        # المتوسطات المتحركة
        for period in [5, 10, 20, 50, 200]:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            df[f'distance_sma_{period}'] = (df['close'] - df[f'sma_{period}']) / df[f'sma_{period}']
        
        # RSI
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        df['rsi_7'] = self._calculate_rsi(df['close'], 7)
        
        # MACD
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        df['atr_14'] = self._calculate_atr(df, 14)
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ميزات الحجم"""
        # المتوسط المتحرك للحجم
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # تغير الحجم
        df['volume_change'] = df['volume'].pct_change()
        
        # حجم OBV
        df['obv'] = self._calculate_obv(df)
        
        # حجم المتوسط المتحرك
        for period in [5, 10, 20]:
            df[f'volume_ma_{period}'] = df['volume'].rolling(window=period).mean()
        
        return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """الميزات الإحصائية"""
        windows = [5, 10, 20, 50]
        
        for window in windows:
            # الانحراف المعياري
            df[f'std_{window}'] = df['close'].rolling(window=window).std()
            
            # الانحراف
            df[f'skew_{window}'] = df['close'].rolling(window=window).skew()
            
            # التفرطح
            df[f'kurt_{window}'] = df['close'].rolling(window=window).kurt()
            
            # النطاق
            df[f'range_{window}'] = df['high'].rolling(window=window).max() - df['low'].rolling(window=window).min()
            
            # Z-score
            rolling_mean = df['close'].rolling(window=window).mean()
            rolling_std = df['close'].rolling(window=window).std()
            df[f'zscore_{window}'] = (df['close'] - rolling_mean) / rolling_std
        
        # الارتباط الذاتي
        df['autocorr_1'] = df['returns'].rolling(window=20).apply(
            lambda x: x.autocorr(lag=1), raw=False
        )
        
        return df
    
    def _add_time_series_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ميزات السلاسل الزمنية"""
        # الاتجاه
        df['trend_10'] = np.where(df['close'] > df['close'].shift(10), 1, -1)
        df['trend_20'] = np.where(df['close'] > df['close'].shift(20), 1, -1)
        
        # الاتجاه المتوسط المتحرك
        df['trend_sma_fast'] = np.where(df['sma_10'] > df['sma_20'], 1, -1)
        df['trend_sma_slow'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
        
        # التسارع
        df['momentum_10'] = df['close'] - df['close'].shift(10)
        df['momentum_20'] = df['close'] - df['close'].shift(20)
        
        # معدل التغير
        df['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
        
        return df
    
    def _add_lagged_features(self, df: pd.DataFrame, lags: List[int] = None) -> pd.DataFrame:
        """الميزات المتأخرة"""
        if lags is None:
            lags = [1, 2, 3, 5, 8, 13, 21]
        
        features_to_lag = ['close', 'volume', 'returns', 'rsi_14', 'macd']
        
        for feature in features_to_lag:
            if feature in df.columns:
                for lag in lags:
                    df[f'{feature}_lag_{lag}'] = df[feature].shift(lag)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """حساب RSI"""
        delta = prices.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """حساب ATR"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        atr = true_range.rolling(period).mean()
        return atr
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """حساب On-Balance Volume"""
        obv = [0]
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=df.index)
    
    def prepare_ml_dataset(
        self,
        df: pd.DataFrame,
        target_horizon: int = 5,
        train_split: float = 0.8
    ) -> Dict:
        """
        إعداد مجموعة بيانات للتعلم الآلي
        """
        # إنشاء الهدف (الحركة المستقبلية)
        df['target'] = df['close'].shift(-target_horizon) / df['close'] - 1
        
        # تصنيف الهدف
        df['target_class'] = pd.cut(
            df['target'],
            bins=[-np.inf, -0.005, 0.005, np.inf],
            labels=[0, 1, 2]  # Down, Neutral, Up
        )
        
        # اختيار الميزات الرقمية فقط
        feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in feature_cols if c not in ['target', 'target_class']]
        
        # إزالة NaN
        df_clean = df.dropna()
        
        # تقسيم البيانات
        split_idx = int(len(df_clean) * train_split)
        
        train_data = df_clean.iloc[:split_idx]
        test_data = df_clean.iloc[split_idx:]
        
        X_train = train_data[feature_cols].values
        y_train = train_data['target_class'].values
        X_test = test_data[feature_cols].values
        y_test = test_data['target_class'].values
        
        # تطبيع
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return {
            'X_train': X_train_scaled,
            'X_test': X_test_scaled,
            'y_train': y_train,
            'y_test': y_test,
            'feature_names': feature_cols,
            'scaler': self.scaler,
            'dates_train': train_data.index,
            'dates_test': test_data.index
        }
    
    def get_feature_importance(self, model, feature_names: List[str]) -> Dict[str, float]:
        """استخراج أهمية الميزات"""
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importances = np.abs(model.coef_[0])
        else:
            return {}
        
        return dict(sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True
        ))
