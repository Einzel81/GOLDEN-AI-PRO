"""
اختبارات تكامل MT5
"""

import pytest
import asyncio
from src.data.connectors.mt5_connector import MT5Connector, TradeRequest


@pytest.mark.integration
class TestMT5Connector:
    """اختبارات تكامل MT5 (تتطلب MT5 مشغلاً)"""
    
    @pytest.fixture
    async def connector(self):
        """إنشاء موصل"""
        conn = MT5Connector()
        yield conn
        await conn.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection(self, connector):
        """اختبار الاتصال"""
        connected = await connector.connect()
        
        # قد يفشل إذا لم يكن MT5 متاحاً
        if connected:
            assert connector.connected is True
            assert connector.account_info is not None
    
    @pytest.mark.asyncio
    async def test_get_rates(self, connector):
        """اختبار جلب البيانات"""
        connected = await connector.connect()
        
        if not connected:
            pytest.skip("MT5 not available")
        
        df = await connector.get_rates('XAUUSD', 'H1', count=100)
        
        assert len(df) > 0
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
    
    @pytest.mark.asyncio
    async def test_health_check(self, connector):
        """اختبار فحص الصحة"""
        health = await connector.health_check()
        
        assert 'status' in health
        
        if connector.connected:
            assert health['status'] == 'connected'
        else:
            assert health['status'] == 'disconnected'
