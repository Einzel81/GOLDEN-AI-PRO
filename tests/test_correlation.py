"""
اختبارات وحدة شاملة لنظام الارتباطات
تغطي جميع المكونات الجديدة
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# إضافة المسار الرئيسي
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from ml.features import FeatureEngineer, extract_features
from analysis.correlation_engine import CorrelationAnalyzer, DivergenceType, CorrelationSignal
from data.multi_asset_collector import MultiAssetDataCollector
from strategies.correlation_strategy import DXYCorrelationStrategy, TradingDecision


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_config():
    """إعدادات تجريبية"""
    return {
        'GOLD_SYMBOL': 'XAUUSD',
        'DXY_SYMBOL': 'DX1',
        'SILVER_SYMBOL': 'XAGUSD',
        'CORR_WINDOW_SHORT': 10,
        'CORR_WINDOW_MEDIUM': 20,
        'CORR_WINDOW_LONG': 50,
        'ENABLE_DXY_ANALYSIS': True,
        'MIN_CONFIDENCE': 0.65,
        'MAX_CORRELATION_BOOST': 0.20
    }


@pytest.fixture
def mock_gold_data():
    """بيانات ذهب وهمية"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='H')
    prices = 2000 + np.cumsum(np.random.randn(100) * 0.5)
    
    return pd.DataFrame({
        'open': prices * 0.999,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)


@pytest.fixture
def mock_market_data(mock_gold_data):
    """بيانات سوق متعددة وهمية"""
    dates = mock_gold_data.index
    
    # DXY مع ارتباط سلبي (~-0.85)
    dxy_prices = 100 + np.cumsum(-0.85 * np.diff(mock_gold_data['close'], 
                                                  prepend=mock_gold_data['close'].iloc[0]) * 0.01 
                                  + np.random.randn(100) * 0.1)
    
    # الفضة مع ارتباط إيجابي (~+0.75)
    silver_prices = 24 + np.cumsum(0.75 * np.diff(mock_gold_data['close'], 
                                                   prepend=mock_gold_data['close'].iloc[0]) * 0.001 
                                    + np.random.randn(100) * 0.05)
    
    return {
        'gold': mock_gold_data,
        'dollar_index': pd.DataFrame({
            'open': dxy_prices * 0.999,
            'high': dxy_prices * 1.001,
            'low': dxy_prices * 0.999,
            'close': dxy_prices,
            'volume': np.random.randint(5000, 20000, 100)
        }, index=dates),
        'silver': pd.DataFrame({
            'open': silver_prices * 0.999,
            'high': silver_prices * 1.005,
            'low': silver_prices * 0.995,
            'close': silver_prices,
            'volume': np.random.randint(2000, 8000, 100)
        }, index=dates)
    }


# ============================================================
# اختبارات FeatureEngineer
# ============================================================

class TestFeatureEngineer:
    
    def test_base_features(self, mock_gold_data):
        """اختبار الميزات الأساسية"""
        engineer = FeatureEngineer()
        features = engineer.create_base_features(mock_gold_data)
        
        assert 'returns' in features.columns
        assert 'log_returns' in features.columns
        assert 'range' in features.columns
        assert len(features) == len(mock_gold_data)
    
    def test_momentum_features(self, mock_gold_data):
        """اختبار ميزات الزخم"""
        engineer = FeatureEngineer()
        base = engineer.create_base_features(mock_gold_data)
        features = engineer.add_momentum_features(base)
        
        assert 'rsi_14' in features.columns
        assert 'macd' in features.columns
        assert 'ema_20' in features.columns
        assert features['rsi_14'].between(0, 100).all()
    
    def test_correlation_features(self, mock_gold_data, mock_market_data):
        """اختبار ميزات الارتباط"""
        engineer = FeatureEngineer()
        base = engineer.create_base_features(mock_gold_data)
        features = engineer.add_correlation_features(base, mock_market_data)
        
        assert 'dxy_close' in features.columns
        assert 'dxy_returns' in features.columns
        assert 'silver_close' in features.columns
        assert 'gold_silver_ratio' in features.columns
        assert 'corr_gold_dxy_20' in features.columns
        
        # التحقق من الارتباط السلبي
        corr = features['corr_gold_dxy_20'].dropna().mean()
        assert corr < -0.3  # يجب أن يكون سلبياً
    
    def test_cross_asset_momentum(self, mock_gold_data, mock_market_data):
        """اختبار زخم الأصول المتعددة"""
        engineer = FeatureEngineer()
        base = engineer.create_base_features(mock_gold_data)
        base = engineer.add_correlation_features(base, mock_market_data)
        features = engineer.add_cross_asset_momentum(base)
        
        assert 'momentum_divergence' in features.columns
        assert 'divergence_signal' in features.columns
    
    def test_full_pipeline(self, mock_gold_data, mock_market_data):
        """اختبار خط الأنابيب الكامل"""
        engineer = FeatureEngineer()
        features = engineer.create_full_feature_set(mock_gold_data, mock_market_data)
        
        assert len(features) > 0
        assert len(features.columns) > 50  # يجب أن يكون هناك العديد من الميزات
        assert features.isna().sum().sum() == 0  # لا قيم فارغة


# ============================================================
# اختبارات CorrelationAnalyzer
# ============================================================

class TestCorrelationAnalyzer:
    
    def test_rolling_correlation(self, mock_gold_data, mock_market_data):
        """اختبار الارتباط المتحرك"""
        analyzer = CorrelationAnalyzer()
        
        corr = analyzer.calculate_rolling_correlation(
            mock_gold_data['close'],
            mock_market_data['dollar_index']['close'],
            window=20
        )
        
        assert len(corr) == len(mock_gold_data)
        assert corr.dropna().between(-1, 1).all()
        assert corr.dropna().mean() < -0.5  # ارتباط سلبي قوي
    
    def test_dxy_trend_detection(self):
        """اختبار كشف اتجاه الدولار"""
        analyzer = CorrelationAnalyzer()
        
        # اتجاه صعودي قوي
        bullish_dxy = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        })
        trend = analyzer.analyze_dxy_trend(bullish_dxy)
        
        assert trend['trend'] in ['STRONG_BULLISH', 'BULLISH']
        assert trend['strength'] > 0.5
        
        # اتجاه هبوطي قوي
        bearish_dxy = pd.DataFrame({
            'close': [110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100]
        })
        trend = analyzer.analyze_dxy_trend(bearish_dxy)
        
        assert trend['trend'] in ['STRONG_BEARISH', 'BEARISH']
    
    def test_divergence_detection_bullish(self):
        """اختبار كشف التباعد الصعودي"""
        analyzer = CorrelationAnalyzer()
        
        # تباعد صعودي: الذهب يرتفع + الدولار يرتفع (نادر)
        gold = pd.DataFrame({'close': [2000, 2050]})
        dxy = pd.DataFrame({'close': [100, 102]})
        
        div = analyzer.detect_divergence(gold, dxy, lookback=1)
        assert div == DivergenceType.BULLISH
    
    def test_divergence_detection_bearish(self):
        """اختبار كشف التباعد الهبوطي"""
        analyzer = CorrelationAnalyzer()
        
        # تباعد هبوطي: الذهب ينخفض + الدولار ينخفض (نادر)
        gold = pd.DataFrame({'close': [2000, 1950]})
        dxy = pd.DataFrame({'close': [100, 98]})
        
        div = analyzer.detect_divergence(gold, dxy, lookback=1)
        assert div == DivergenceType.BEARISH
    
    def test_generate_correlation_signal(self, mock_gold_data, mock_market_data):
        """اختبار توليد الإشارة الكاملة"""
        analyzer = CorrelationAnalyzer()
        
        signal = analyzer.generate_correlation_signal(
            mock_gold_data,
            mock_market_data['dollar_index'],
            mock_market_data.get('silver')
        )
        
        assert isinstance(signal, CorrelationSignal)
        assert -1 <= signal.correlation <= 1
        assert signal.strength >= 0
        assert signal.recommendation in ['strong_buy', 'buy', 'neutral', 'sell', 'strong_sell']
    
    def test_leading_indicators(self, mock_market_data):
        """اختبار المؤشرات القيادية"""
        analyzer = CorrelationAnalyzer()
        indicators = analyzer.calculate_leading_indicators(mock_market_data)
        
        assert 'silver_lead' in indicators or 'gold_silver_ratio' in indicators


# ============================================================
# اختبارات DXYCorrelationStrategy
# ============================================================

class TestDXYCorrelationStrategy:
    
    def test_combine_signals_buy_confirmation(self):
        """اختبار تأكيد إشارة الشراء"""
        strategy = DXYCorrelationStrategy()
        
        gold_signal = {'action': 'BUY', 'confidence': 0.7}
        corr_signal = CorrelationSignal(
            correlation=-0.85,
            dxy_trend='STRONG_BEARISH',
            divergence=DivergenceType.NONE,
            strength=0.9,
            recommendation='strong_buy',
            confidence_boost=0.20
        )
        
        decision = strategy.combine_signals(gold_signal, corr_signal)
        
        assert decision.action == 'BUY'
        assert decision.confidence > 0.8
        assert decision.position_size_multiplier > 1.0
    
    def test_combine_signals_sell_confirmation(self):
        """اختبار تأكيد إشارة البيع"""
        strategy = DXYCorrelationStrategy()
        
        gold_signal = {'action': 'SELL', 'confidence': 0.7}
        corr_signal = CorrelationSignal(
            correlation=-0.85,
            dxy_trend='STRONG_BULLISH',
            divergence=DivergenceType.NONE,
            strength=0.9,
            recommendation='strong_sell',
            confidence_boost=-0.20
        )
        
        decision = strategy.combine_signals(gold_signal, corr_signal)
        
        assert decision.action == 'SELL'
        assert decision.confidence > 0.8
    
    def test_combine_signals_conflict(self):
        """اختبار التعارض بين الإشارات"""
        strategy = DXYCorrelationStrategy()
        
        gold_signal = {'action': 'BUY', 'confidence': 0.6}
        corr_signal = CorrelationSignal(
            correlation=-0.85,
            dxy_trend='STRONG_BULLISH',
            divergence=DivergenceType.NONE,
            strength=0.9,
            recommendation='strong_sell',
            confidence_boost=-0.15
        )
        
        decision = strategy.combine_signals(gold_signal, corr_signal)
        
        # يجب أن يقلل الثقة أو يمنع الصفقة
        assert decision.confidence < 0.6 or decision.action == 'HOLD'
    
    def test_divergence_boost(self):
        """اختبار تأثير التباعد النادر"""
        strategy = DXYCorrelationStrategy()
        
        gold_signal = {'action': 'BUY', 'confidence': 0.7}
        corr_signal = CorrelationSignal(
            correlation=-0.85,
            dxy_trend='NEUTRAL',
            divergence=DivergenceType.BULLISH,
            strength=0.9,
            recommendation='buy',
            confidence_boost=0.25
        )
        
        decision = strategy.combine_signals(gold_signal, corr_signal)
        
        assert decision.position_size_multiplier >= 1.5
    
    def test_filter_trade(self):
        """اختبار فلترة الصفقات"""
        strategy = DXYCorrelationStrategy()
        
        # صفقة شراء ضد الدولار القوي - يجب رفضها
        gold_signal = {'action': 'BUY', 'confidence': 0.6}
        context = {
            'dxy_analysis': {'trend': 'STRONG_BULLISH'},
            'correlations': {'medium_term': -0.8}
        }
        
        should_filter = strategy.should_filter_trade(gold_signal, context)
        assert should_filter == True


# ============================================================
# اختبارات MultiAssetDataCollector
# ============================================================

class TestMultiAssetDataCollector:
    
    def test_initialization(self, sample_config):
        """اختبار التهيئة"""
        collector = MultiAssetDataCollector(sample_config)
        
        assert collector.symbols['gold'] == 'XAUUSD'
        assert collector.symbols['dollar_index'] == 'DX1'
        assert collector.timeframe == 'H1'
    
    def test_fetch_ohlc_mock(self, mock_gold_data, sample_config, monkeypatch):
        """اختبار جلب البيانات (محاكاة)"""
        collector = MultiAssetDataCollector(sample_config)
        
        # محاكاة MT5
        def mock_copy_rates(*args, **kwargs):
            return mock_gold_data.reset_index().to_dict('records')
        
        monkeypatch.setattr('data.multi_asset_collector.copy_rates_from_pos', mock_copy_rates)
        monkeypatch.setattr('data.multi_asset_collector.initialize', lambda: True)
        
        result = collector.fetch_ohlc('XAUUSD')
        assert result is not None
        assert len(result) == len(mock_gold_data)
    
    def test_correlation_matrix(self, mock_market_data, sample_config):
        """اختبار حساب مصفوفة الارتباط"""
        collector = MultiAssetDataCollector(sample_config)
        
        corr_matrix = collector.get_correlation_matrix(mock_market_data, window=20)
        
        assert not corr_matrix.empty
        assert 'gold' in corr_matrix.index.get_level_values(0)
        assert 'dollar_index' in corr_matrix.index.get_level_values(0)
    
    def test_gold_silver_ratio(self, mock_market_data, sample_config):
        """اختبار حساب النسبة"""
        collector = MultiAssetDataCollector(sample_config)
        
        ratio = collector.calculate_gold_silver_ratio(
            mock_market_data['gold'],
            mock_market_data['silver']
        )
        
        assert len(ratio) > 0
        assert ratio.mean() > 50  # النسبة التاريخية عادة 60-80


# ============================================================
# اختبارات التكامل
# ============================================================

class TestIntegration:
    
    def test_full_pipeline(self, mock_gold_data, mock_market_data, sample_config):
        """اختبار خط الأنابيب الكامل"""
        # 1. استخراج الميزات
        engineer = FeatureEngineer(sample_config)
        features = engineer.create_full_feature_set(mock_gold_data, mock_market_data)
        
        # 2. تحليل الارتباط
        analyzer = CorrelationAnalyzer(sample_config)
        corr_signal = analyzer.generate_correlation_signal(
            mock_gold_data,
            mock_market_data['dollar_index'],
            mock_market_data.get('silver')
        )
        
        # 3. اتخاذ القرار
        strategy = DXYCorrelationStrategy(sample_config)
        technical_signal = {
            'action': 'BUY',
            'confidence': 0.75,
            'current_price': mock_gold_data['close'].iloc[-1]
        }
        
        decision = strategy.combine_signals(technical_signal, corr_signal)
        
        # التحقق من النتيجة
        assert decision.action in ['BUY', 'SELL', 'HOLD']
        assert 0 <= decision.confidence <= 1
        assert decision.position_size_multiplier > 0
        
        # 4. التحقق من الميزات
        assert 'dxy_close' in features.columns
        assert 'corr_gold_dxy_20' in features.columns
    
    def test_end_to_end_api(self, mock_gold_data, mock_market_data, sample_config):
        """اختبار كامل للـ API"""
        from api.main import GoldenAIPro
        
        # محاكاة النظام
        system = GoldenAIPro()
        system.config = sample_config
        
        # محاكاة البيانات
        system.data_collector = MultiAssetDataCollector(sample_config)
        system.is_initialized = True
        
        # اختبار التحليل
        technical = system.analyze_technical(mock_gold_data)
        assert 'action' in technical
        assert 'confidence' in technical
        
        # اختبار الارتباط
        corr = system.analyze_correlation(mock_gold_data, mock_market_data)
        if corr:
            assert hasattr(corr, 'correlation')
            assert hasattr(corr, 'recommendation')


# ============================================================
# تشغيل الاختبارات
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
