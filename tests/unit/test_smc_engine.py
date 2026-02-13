"""
اختبارات محرك SMC
"""

import pytest
import pandas as pd
import numpy as np
from src.analysis.smc.smc_engine import SMCEngine, SignalType


@pytest.fixture
def sample_data():
    """بيانات عينة"""
    dates = pd.date_range('2024-01-01', periods=100, freq='H')
    np.random.seed(42)
    
    data = {
        'open': 1900 + np.random.randn(100).cumsum() * 5,
        'high': 1905 + np.random.randn(100).cumsum() * 5,
        'low': 1895 + np.random.randn(100).cumsum() * 5,
        'close': 1900 + np.random.randn(100).cumsum() * 5,
        'volume': np.random.randint(1000, 10000, 100)
    }
    
    df = pd.DataFrame(data, index=dates)
    df['high'] = df[['open', 'close', 'high']].max(axis=1) + 2
    df['low'] = df[['open', 'close', 'low']].min(axis=1) - 2
    
    return df


class TestSMCEngine:
    """اختبارات محرك SMC"""
    
    def test_initialization(self):
        """اختبار التهيئة"""
        engine = SMCEngine()
        assert engine is not None
        assert engine.min_confidence == 0.65
    
    def test_analyze_returns_signal(self, sample_data):
        """اختبار أن التحليل يعيد إشارة"""
        engine = SMCEngine()
        signal = engine.analyze(sample_data, timeframe='H1')
        
        assert signal is not None
        assert isinstance(signal.type, SignalType)
        assert 0 <= signal.confidence <= 1
    
    def test_signal_components(self, sample_data):
        """اختبار مكونات الإشارة"""
        engine = SMCEngine()
        signal = engine.analyze(sample_data, timeframe='H1')
        
        assert hasattr(signal, 'entry_price')
        assert hasattr(signal, 'stop_loss')
        assert hasattr(signal, 'take_profit')
        assert hasattr(signal, 'order_blocks')
        assert hasattr(signal, 'fvgs')
    
    def test_multi_timeframe_analysis(self, sample_data):
        """اختبار التحليل متعدد الأطر"""
        engine = SMCEngine()
        
        data_dict = {
            'H1': sample_data,
            'H4': sample_data.resample('4H').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
        }
        
        signals = engine.multi_timeframe_analysis(data_dict)
        
        assert 'H1' in signals
        assert 'H4' in signals
    
    def test_empty_data_handling(self):
        """اختبار التعامل مع البيانات الفارغة"""
        engine = SMCEngine()
        empty_df = pd.DataFrame()
        
        signal = engine.analyze(empty_df, timeframe='H1')
        
        assert signal.type == SignalType.NEUTRAL
        assert signal.confidence == 0.0
    
    def test_insufficient_data(self):
        """اختبار البيانات غير الكافية"""
        engine = SMCEngine()
        small_df = pd.DataFrame({
            'open': [1900, 1901],
            'high': [1902, 1903],
            'low': [1899, 1900],
            'close': [1901, 1902],
            'volume': [1000, 2000]
        })
        
        signal = engine.analyze(small_df, timeframe='H1')
        
        assert signal.type == SignalType.NEUTRAL
