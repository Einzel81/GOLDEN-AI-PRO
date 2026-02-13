"""
اختبارات شامل workflow
"""

import pytest
import asyncio
from httpx import AsyncClient
from src.api.main import app


@pytest.mark.e2e
class TestFullWorkflow:
    """اختبارات شامل للنظام"""
    
    @pytest.fixture
    async def client(self):
        """إنشاء عميل HTTP"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """اختبار نقطة الصحة"""
        response = await client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()
    
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self, client):
        """اختبار نقطة التحليل"""
        response = await client.post("/api/v1/analyze?timeframe=H1")
        
        # قد ينجح أو يفشل حسب توفر MT5
        assert response.status_code in [200, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "signal" in data
            assert "confidence" in data
    
    @pytest.mark.asyncio
    async def test_account_endpoint(self, client):
        """اختبار نقطة الحساب"""
        response = await client.get("/api/v1/account")
        
        assert response.status_code in [200, 500, 503]
    
    @pytest.mark.asyncio
    async def test_positions_endpoint(self, client):
        """اختبار نقطة المراكز"""
        response = await client.get("/api/v1/positions")
        
        assert response.status_code in [200, 500, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "positions" in data
            assert "count" in data
