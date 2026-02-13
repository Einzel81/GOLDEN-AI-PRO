"""
محرك استخراج الميزات للنماذج التنبؤية
يدمج تحليل الذهب مع DXY والمعادن الأخرى
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from scipy.stats import zscore

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    مهندس الميزات الرئيسي - يدعم التحليل متعدد الأصول
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.lookback_periods = self.config.get('LOOKBACK_PERIODS', [5, 10, 20, 50])
        self.volume_enabled = self.config.get('ENABLE_VOLUME_FEATURES', True)
        
    # ============================================================
    # الميزات الأساسية للذهب
    # ============================================================
    
    def create_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        إنشاء الميزات الأساسية للسعر والزخم
        """
        features = pd.DataFrame(index=df.index)
        
        # الأسعار
        features['open'] = df['open']
        features['high'] = df['high']
        features['low'] = df['low']
        features['close'] = df['close']
        features['volume'] = df.get('volume', 0)
        
        # العوائد
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # المدى
        features['range'] = df['high'] - df['low']
        features['range_pct'] = features['range'] / df['close']
        features['body'] = abs(df['close'] - df['open'])
        features['upper_shadow'] = df['high'] - df[['close', 'open']].max(axis=1)
        features['lower_shadow'] = df[['close', 'open']].min(axis=1) - df['low']
        
        # الشموع
        features['is_bullish'] = (df['close'] > df['open']).astype(int)
        
        return features
    
    def add_momentum_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        إضافة مؤشرات الزخم
        """
        close = features['close']
        
        for period in self.lookback_periods:
            # العوائد المتأخرة
            features[f'return_{period}h'] = close.pct_change(period)
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            features[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            
            # المتوسطات المتحركة
            features[f'ema_{period}'] = close.ewm(span=period, adjust=False).mean()
            features[f'sma_{period}'] = close.rolling(window=period).mean()
            
            # المسافة عن المتوسط
            features[f'dist_ema_{period}'] = (close - features[f'ema_{period}']) / close
            
            # التقلب
            features[f'volatility_{period}'] = features['returns'].rolling(period).std()
        
        # MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        features['macd'] = ema_12 - ema_26
        features['macd_signal'] = features['macd'].ewm(span=9, adjust=False).mean()
        features['macd_hist'] = features['macd'] - features['macd_signal']
        
        return features
    
    def add_volume_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        إضافة ميزات حجم التداول
        """
        if 'volume' not in features.columns or not self.volume_enabled:
            return features
        
        volume = features['volume']
        close = features['close']
        
        # متوسط الحجم
        for period in [10, 20, 50]:
            features[f'volume_sma_{period}'] = volume.rolling(period).mean()
            features[f'volume_ratio_{period}'] = volume / features[f'volume_sma_{period}']
        
        # OBV (On Balance Volume)
        obv = [0]
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.append(obv[-1] + volume.iloc[i])
            elif close.iloc[i] < close.iloc[i-1]:
                obv.append(obv[-1] - volume.iloc[i])
            else:
                obv.append(obv[-1])
        features['obv'] = obv
        
        # VWAP
        typical_price = (features['high'] + features['low'] + features['close']) / 3
        features['vwap'] = (typical_price * volume).cumsum() / volume.cumsum()
        features['dist_vwap'] = (close - features['vwap']) / close
        
        return features
    
    def add_price_action_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        إضافة أنماط Price Action
        """
        open_p = features['open']
        high = features['high']
        low = features['low']
        close = features['close']
        
        # أنماط الشموع
        body = abs(close - open_p)
        range_total = high - low
        
        # Doji
        features['is_doji'] = (body <= 0.1 * range_total).astype(int)
        
        # Hammer / Shooting Star
        features['lower_shadow_ratio'] = features['lower_shadow'] / range_total
        features['upper_shadow_ratio'] = features['upper_shadow'] / range_total
        features['is_hammer'] = ((features['lower_shadow_ratio'] > 0.6) & 
                                  (features['upper_shadow_ratio'] < 0.1)).astype(int)
        features['is_shooting_star'] = ((features['upper_shadow_ratio'] > 0.6) & 
                                         (features['lower_shadow_ratio'] < 0.1)).astype(int)
        
        # Engulfing
        prev_close = close.shift(1)
        prev_open = open_p.shift(1)
        features['bullish_engulfing'] = ((open_p < prev_close) & 
                                          (close > prev_open) & 
                                          (close > prev_close) & 
                                          (open_p < prev_open)).astype(int)
        features['bearish_engulfing'] = ((open_p > prev_close) & 
                                          (close < prev_open) & 
                                          (close < prev_close) & 
                                          (open_p > prev_open)).astype(int)
        
        return features
    
    # ============================================================
    # ميزات الارتباطات الجديدة (DXY والمعادن)
    # ============================================================
    
    def add_correlation_features(self, 
                                  features: pd.DataFrame,
                                  market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        إضافة ميزات الارتباط مع DXY والمعادن
        """
        if not market_data:
            return features
        
        # 1. مؤشر الدولار (DXY/DX1)
        if 'dollar_index' in market_data:
            dxy = market_data['dollar_index']
            dxy_aligned = dxy.reindex(features.index, method='ffill')
            
            # الأسعار والتغيرات
            features['dxy_close'] = dxy_aligned['close']
            features['dxy_open'] = dxy_aligned['open']
            features['dxy_high'] = dxy_aligned['high']
            features['dxy_low'] = dxy_aligned['low']
            
            # العوائد
            features['dxy_returns'] = features['dxy_close'].pct_change()
            features['dxy_returns_4h'] = features['dxy_close'].pct_change(4)
            features['dxy_returns_1d'] = features['dxy_close'].pct_change(24)
            
            # المتوسطات المتحركة
            for period in [10, 20, 50]:
                features[f'dxy_ema_{period}'] = features['dxy_close'].ewm(span=period).mean()
                features[f'dxy_sma_{period}'] = features['dxy_close'].rolling(period).mean()
            
            # الاتجاه
            features['dxy_above_ema20'] = (features['dxy_close'] > features['dxy_ema_20']).astype(int)
            features['dxy_above_ema50'] = (features['dxy_close'] > features['dxy_ema_50']).astype(int)
            features['dxy_trend'] = np.where(
                features['dxy_close'] > features['dxy_ema_20'], 1,
                np.where(features['dxy_close'] < features['dxy_ema_20'], -1, 0)
            )
            
            # القوة النسبية
            features['dxy_rsi'] = self._calculate_rsi(features['dxy_close'], 14)
            
            logger.debug("تم إضافة ميزات DXY")
        
        # 2. الفضة (مؤشر قيادي)
        if 'silver' in market_data:
            silver = market_data['silver']
            silver_aligned = silver.reindex(features.index, method='ffill')
            
            features['silver_close'] = silver_aligned['close']
            features['silver_returns'] = features['silver_close'].pct_change()
            features['silver_rsi'] = self._calculate_rsi(features['silver_close'], 14)
            
            # نسبة الذهب/الفضة
            features['gold_silver_ratio'] = features['close'] / features['silver_close']
            features['ratio_change'] = features['gold_silver_ratio'].pct_change()
            features['ratio_zscore'] = zscore(features['gold_silver_ratio'].fillna(
                features['gold_silver_ratio'].mean()
            ))
            
            # الفضة تسبق الذهب؟
            features['silver_momentum'] = features['silver_returns'].rolling(5).sum()
            features['silver_leads'] = (features['silver_momentum'].shift(1) * 
                                         features['returns'] > 0).astype(int)
            
            logger.debug("تم إضافة ميزات الفضة")
        
        # 3. المعادن الأخرى
        for metal in ['platinum', 'palladium', 'copper']:
            if metal in market_data:
                metal_df = market_data[metal]
                metal_aligned = metal_df.reindex(features.index, method='ffill')
                
                features[f'{metal}_close'] = metal_aligned['close']
                features[f'{metal}_returns'] = features[f'{metal}_close'].pct_change()
                
                # الارتباط مع الذهب
                gold_returns = features['returns']
                metal_returns = features[f'{metal}_returns']
                features[f'corr_gold_{metal}_20'] = gold_returns.rolling(20).corr(metal_returns)
        
        # 4. الارتباطات المتحركة (الأهم)
        if 'dollar_index' in market_data:
            gold_returns = features['returns']
            dxy_returns = features['dxy_returns']
            
            # ارتباط الذهب/الدولار متعدد الفترات
            for window in [10, 20, 50]:
                features[f'corr_gold_dxy_{window}'] = gold_returns.rolling(window).corr(dxy_returns)
            
            # تغير الارتباط (انقلاب الارتباط إشارة قوية)
            features['corr_change'] = features['corr_gold_dxy_10'] - features['corr_gold_dxy_50']
            
            # قوة الارتباط الحالية
            features['correlation_strength'] = abs(features['corr_gold_dxy_20'])
            
            # انحراف الارتباط عن المتوسط
            mean_corr = features['corr_gold_dxy_20'].rolling(100).mean()
            features['corr_deviation'] = features['corr_gold_dxy_20'] - mean_corr
        
        return features
    
    def add_cross_asset_momentum(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        إضافة زخم الأصول المتعددة والتباعدات
        """
        if 'dxy_returns' not in features.columns:
            return features
        
        # 1. تباعد الذهب/الدولار (العائدات)
        features['momentum_divergence'] = features['returns'] - (-features['dxy_returns'])
        # قيمة موجبة = الذهب أقوى من المتوقع مقابل الدولار
        
        # 2. تباعد الزخم
        gold_momentum = features['returns'].rolling(10).sum()
        dxy_momentum = features['dxy_returns'].rolling(10).sum()
        features['momentum_divergence_10h'] = gold_momentum - (-dxy_momentum)
        
        # 3. إشارة التباعد
        features['divergence_signal'] = 0
        features.loc[features['momentum_divergence'] > 0.005, 'divergence_signal'] = 1  # صعودي
        features.loc[features['momentum_divergence'] < -0.005, 'divergence_signal'] = -1  # هبوطي
        
        # 4. قوة الدولار مقسومة على قوة الذهب
        features['relative_strength'] = abs(features['dxy_returns']) / (abs(features['returns']) + 0.0001)
        
        # 5. إذا كانت الفضة متوفرة
        if 'silver_returns' in features.columns:
            # الفضة تتحرك قبل الذهب؟
            features['silver_gold_lead'] = features['silver_returns'].shift(2).rolling(3).corr(
                features['returns']
            )
        
        return features
    
    def add_smc_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        إضافة ميزات Smart Money Concepts
        """
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df.get('volume', pd.Series(1, index=df.index))
        
        # Order Blocks (تقريبي)
        for period in [5, 10]:
            # آخر قمة/قاع
            features[f'highest_{period}'] = high.rolling(period).max()
            features[f'lowest_{period}'] = low.rolling(period).min()
            
            # المسافة من القمة/القاع
            features[f'dist_from_high_{period}'] = (close - features[f'highest_{period}']) / close
            features[f'dist_from_low_{period}'] = (close - features[f'lowest_{period}']) / close
        
        # Fair Value Gaps (FVG)
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        features['fvg_bullish'] = (low > prev_high).astype(int)  # فجوة صعودية
        features['fvg_bearish'] = (high < prev_low).astype(int)  # فجوة هبوطية
        
        # Liquidity Sweeps (مسح السيولة)
        features['sweep_high'] = ((high >= features['highest_10'].shift(1)) & 
                                   (close < high)).astype(int)
        features['sweep_low'] = ((low <= features['lowest_10'].shift(1)) & 
                                  (close > low)).astype(int)
        
        # Volume Profile (تقريبي)
        if 'volume' in df.columns:
            features['volume_delta'] = np.where(close > df['open'], volume, -volume)
            features['volume_delta_cum'] = features['volume_delta'].cumsum()
            
            # POC (Point of Control) - تقريبي
            vol_profile = features.groupby(pd.cut(close, bins=50))['volume'].sum()
            if not vol_profile.empty:
                poc_price = vol_profile.idxmax().mid
                features['dist_from_poc'] = (close - poc_price) / close
        
        return features
    
    # ============================================================
    # دوال مساعدة
    # ============================================================
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """حساب RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def prepare_ml_features(self, 
                           features: pd.DataFrame, 
                           target_col: str = None,
                           drop_na: bool = True) -> pd.DataFrame:
        """
        تحضير الميزات النهائية للنماذج ML
        """
        # إزالة الأعمدة غير الرقمية
        numeric_features = features.select_dtypes(include=[np.number])
        
        # معالجة القيم الفارغة
        if drop_na:
            numeric_features = numeric_features.dropna()
        else:
            numeric_features = numeric_features.fillna(method='ffill').fillna(0)
        
        # إزالة الأعمدة الثابتة
        numeric_features = numeric_features.loc[:, numeric_features.std() > 0]
        
        logger.info(f"عدد الميزات النهائية: {len(numeric_features.columns)}")
        
        return numeric_features
    
    def create_full_feature_set(self,
                                 gold_data: pd.DataFrame,
                                 market_data: Dict[str, pd.DataFrame] = None) -> pd.DataFrame:
        """
        إنشاء مجموعة الميزات الكاملة
        """
        logger.info("بدء إنشاء الميزات...")
        
        # 1. الميزات الأساسية
        features = self.create_base_features(gold_data)
        
        # 2. الزخم
        features = self.add_momentum_features(features)
        
        # 3. الحجم
        features = self.add_volume_features(features)
        
        # 4. Price Action
        features = self.add_price_action_features(features)
        
        # 5. SMC
        features = self.add_smc_features(features, gold_data)
        
        # 6. الارتباطات (جديد)
        if market_data:
            features = self.add_correlation_features(features, market_data)
            features = self.add_cross_asset_momentum(features)
        
        # 7. التحضير النهائي
        features = self.prepare_ml_features(features)
        
        logger.info(f"تم إنشاء {len(features.columns)} ميزة")
        
        return features


# ============================================================
# دوال سريعة للاستخدام
# ============================================================

def extract_features(gold_data: pd.DataFrame, 
                     market_data: Dict[str, pd.DataFrame] = None,
                     config: Dict = None) -> pd.DataFrame:
    """
    دالة سريعة لاستخراج الميزات
    """
    engineer = FeatureEngineer(config)
    return engineer.create_full_feature_set(gold_data, market_data)


def get_feature_importance(features_df: pd.DataFrame, 
                           target: pd.Series,
                           top_n: int = 20) -> pd.DataFrame:
    """
    حساب أهمية الميزات (يتطلب sklearn)
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.feature_selection import mutual_info_regression
    
    # إزالة القيم الفارغة
    valid_idx = features_df.dropna().index.intersection(target.dropna().index)
    X = features_df.loc[valid_idx]
    y = target.loc[valid_idx]
    
    # Random Forest importance
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    importance_df = pd.DataFrame({
        'feature': X.columns,
        'rf_importance': rf.feature_importances_
    })
    
    # Mutual Information
    mi_scores = mutual_info_regression(X, y, random_state=42)
    importance_df['mutual_info'] = mi_scores
    
    # الترتيب
    importance_df['avg_score'] = (importance_df['rf_importance'] + 
                                   importance_df['mutual_info']) / 2
    importance_df = importance_df.sort_values('avg_score', ascending=False)
    
    return importance_df.head(top_n)
