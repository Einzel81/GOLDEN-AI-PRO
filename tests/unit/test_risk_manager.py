"""
اختبارات مدير المخاطر
"""

import pytest
from src.risk.risk_manager import RiskManager, RiskParameters


class TestRiskManager:
    """اختبارات إدارة المخاطر"""
    
    @pytest.fixture
    def risk_manager(self):
        """إنشاء مدير مخاطر للاختبار"""
        return RiskManager()
    
    def test_initialization(self, risk_manager):
        """اختبار التهيئة"""
        assert risk_manager.params is not None
        assert risk_manager.params.max_risk_per_trade == 0.02
    
    def test_position_sizing(self, risk_manager):
        """اختبار حساب حجم المركز"""
        result = risk_manager.calculate_position_size(
            account_balance=10000,
            entry_price=1900,
            stop_loss=1890
        )
        
        assert result['lots'] > 0
        assert result['risk_amount'] > 0
        assert result['risk_percent'] <= 0.02
    
    def test_drawdown_protection(self, risk_manager):
        """اختبار حماية التراجع"""
        # محاكاة خسائر متتالية
        for i in range(3):
            risk_manager.update_after_trade({
                'pnl': -100,
                'balance': 10000 - (i + 1) * 100
            })
        
        # يجب أن يقلل المخاطرة بعد الخسائر
        result = risk_manager.calculate_position_size(
            account_balance=9700,
            entry_price=1900,
            stop_loss=1890
        )
        
        assert result['risk_percent'] < 0.02
    
    def test_trading_allowed_check(self, risk_manager):
        """اختبار التحقق من السماح بالتداول"""
        # في البداية مسموح
        assert risk_manager.check_trade_allowed(10000, 0) is True
        
        # محاكاة وصول الحد الأقصى للخسارة
        risk_manager.current_drawdown = 0.25
        
        assert risk_manager.check_trade_allowed(10000, 0) is False
    
    def test_daily_limit_reset(self, risk_manager):
        """اختبار إعادة تعيين الحد اليومي"""
        risk_manager.daily_pnl = -500
        
        # محاكاة تغيير اليوم
        from datetime import datetime, timedelta
        risk_manager.last_trade_date = datetime.now().date() - timedelta(days=1)
        
        # يجب إعادة التعيين
        risk_manager.calculate_position_size(10000, 1900, 1890)
        
        assert risk_manager.daily_pnl == 0.0
