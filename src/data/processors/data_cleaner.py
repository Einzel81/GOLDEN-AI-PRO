"""
تنظيف البيانات
Data Cleaning and Validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from loguru import logger


class DataCleaner:
    """
    منظف بيانات متقدم
    """
    
    def __init__(self):
        self.issues_found: List[str] = []
        
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        تنظيف DataFrame
        """
        self.issues_found = []
        data = df.copy()
        
        # 1. إزالة القيم المفقودة
        data = self._handle_missing_values(data)
        
        # 2. إزالة التكرارات
        data = self._remove_duplicates(data)
        
        # 3. تصحيح الأسعار الغريبة
        data = self._fix_price_anomalies(data)
        
        # 4. التحقق من التسلسل الزمني
        data = self._validate_timestamps(data)
        
        # 5. إزالة القيم الشاذة
        data = self._remove_outliers(data)
        
        if self.issues_found:
            logger.warning(f"Data cleaning issues: {self.issues_found}")
        
        return data
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """معالجة القيم المفقودة"""
        missing_count = df.isnull().sum().sum()
        
        if missing_count > 0:
            self.issues_found.append(f"Found {missing_count} missing values")
            
            # Forward fill للأسعار
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(method='ffill')
            
            # Fill الحجم بـ 0
            if 'volume' in df.columns:
                df['volume'] = df['volume'].fillna(0)
        
        return df
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """إزالة الصفوف المكررة"""
        initial_len = len(df)
        df = df[~df.index.duplicated(keep='first')]
        
        if len(df) < initial_len:
            self.issues_found.append(f"Removed {initial_len - len(df)} duplicates")
        
        return df
    
    def _fix_price_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """تصحيح الشموع الغريبة"""
        # التحقق من high >= low
        invalid = df[df['high'] < df['low']]
        if len(invalid) > 0:
            self.issues_found.append(f"Found {len(invalid)} invalid HL relationships")
            df.loc[df['high'] < df['low'], ['high', 'low']] = \
                df.loc[df['high'] < df['low'], ['low', 'high']].values
        
        # التحقق من open و close ضمن النطاق
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)
        
        return df
    
    def _validate_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """التحقق من التسلسل الزمني"""
        if not df.index.is_monotonic_increasing:
            self.issues_found.append("Timestamps not sorted")
            df = df.sort_index()
        
        # التحقق من الفجوات الزمنية
        if len(df) > 1:
            time_diff = df.index.to_series().diff().dropna()
            mode_diff = time_diff.mode()[0]
            gaps = time_diff[time_diff > mode_diff * 2]
            
            if len(gaps) > 0:
                self.issues_found.append(f"Found {len(gaps)} time gaps")
        
        return df
    
    def _remove_outliers(self, df: pd.DataFrame, threshold: float = 5.0) -> pd.DataFrame:
        """إزالة القيم الشاذة"""
        returns = df['close'].pct_change().abs()
        outlier_mask = returns > threshold  # أكثر من 500% تغير
        
        if outlier_mask.sum() > 0:
            self.issues_found.append(f"Found {outlier_mask.sum()} price outliers")
            df = df[~outlier_mask]
        
        return df
    
    def validate_quality(self, df: pd.DataFrame) -> Dict:
        """التقييم النوعي للبيانات"""
        return {
            'total_rows': len(df),
            'date_range': {
                'start': df.index[0].isoformat() if len(df) > 0 else None,
                'end': df.index[-1].isoformat() if len(df) > 0 else None
            },
            'missing_values': df.isnull().sum().to_dict(),
            'completeness': (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
            'valid': len(df) > 100 and df.isnull().sum().sum() / (len(df) * len(df.columns)) < 0.05
        }
