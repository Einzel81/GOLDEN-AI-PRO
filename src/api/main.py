"""
واجهة برمجة التطبيقات الرئيسية
FastAPI Main Application
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from loguru import logger

from config.settings import settings
from src.data.connectors.mt5_connector import mt5_connector
from src.analysis.smc.smc_engine import SMCEngine
from src.ai.fusion_engine import FusionEngine
from src.risk.risk_manager import RiskManager
from src.execution.order_manager import OrderManager


# Global instances
smc_engine = SMCEngine()
fusion_engine = FusionEngine()
risk_manager = RiskManager()
order_manager: Optional[OrderManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    # Startup
    logger.info("Starting Golden-AI Pro API...")
    
    # Connect to MT5
    connected = await mt5_connector.connect()
    if not connected:
        logger.warning("MT5 not connected - running in simulation mode")
    
    # Initialize order manager
    global order_manager
    order_manager = OrderManager(mt5_connector, risk_manager)
    
    # Start background tasks
    asyncio.create_task(market_data_updater())
    asyncio.create_task(position_sync_task())
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await mt5_connector.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Advanced Gold Trading AI with SMC and Deep Learning",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background tasks
async def market_data_updater():
    """تحديث بيانات السوق باستمرار"""
    while True:
        try:
            if mt5_connector.connected:
                # جلب آخر بيانات
                tick = await mt5_connector.get_tick(settings.SYMBOL)
                # يمكن إرسالها عبر WebSocket أو تخزينها
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Market data updater error: {e}")
            await asyncio.sleep(5)


async def position_sync_task():
    """مزامنة المراكز بشكل دوري"""
    while True:
        try:
            if order_manager:
                await order_manager.sync_positions()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Position sync error: {e}")
            await asyncio.sleep(60)


# Routes
@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "mt5_connected": mt5_connector.connected
    }


@app.get("/health")
async def health_check():
    """فحص صحة النظام"""
    mt5_health = await mt5_connector.health_check()
    
    return {
        "status": "healthy",
        "mt5": mt5_health,
        "timestamp": settings.APP_NAME
    }


@app.get("/api/v1/account")
async def get_account_info():
    """معلومات الحساب"""
    try:
        info = await mt5_connector.get_account_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/positions")
async def get_positions():
    """المراكز المفتوحة"""
    try:
        positions = await mt5_connector.get_positions()
        return {"positions": positions, "count": len(positions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze")
async def analyze_market(timeframe: str = "H1"):
    """تحليل السوق"""
    try:
        # جلب البيانات
        df = await mt5_connector.get_rates(settings.SYMBOL, timeframe, count=500)
        
        # تحليل SMC
        smc_signal = smc_engine.analyze(df, timeframe)
        
        # يمكن إضافة تحليل AI هنا
        
        return {
            "signal": smc_signal.type.value,
            "confidence": smc_signal.confidence,
            "entry": smc_signal.entry_price,
            "stop_loss": smc_signal.stop_loss,
            "take_profit": smc_signal.take_profit,
            "timeframe": timeframe,
            "timestamp": smc_signal.timestamp.isoformat(),
            "components": {
                "order_blocks": len(smc_signal.order_blocks),
                "fvgs": len(smc_signal.fvgs),
                "liquidity_levels": len(smc_signal.liquidity_levels)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/trade")
async def execute_trade(
    action: str,
    volume: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
):
    """تنفيذ صفقة"""
    try:
        # التحقق من المخاطر
        account_info = await mt5_connector.get_account_info()
        balance = account_info['balance']
        
        if not risk_manager.check_trade_allowed(balance, len(await mt5_connector.get_positions())):
            raise HTTPException(status_code=400, detail="Trading not allowed due to risk limits")
        
        # تنفيذ الأمر
        order = await order_manager.place_order(
            symbol=settings.SYMBOL,
            action=action,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        return {
            "success": order.status == "filled",
            "order_id": order.id,
            "ticket": order.ticket,
            "status": order.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/close/{order_id}")
async def close_trade(order_id: str):
    """إغلاق صفقة"""
    try:
        success = await order_manager.close_position(order_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/risk/status")
async def get_risk_status():
    """حالة المخاطر"""
    return risk_manager.get_risk_report()


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket للتحديثات اللحظية"""
    await websocket.accept()
    try:
        while True:
            # إرسال تحديثات السعر
            if mt5_connector.connected:
                tick = await mt5_connector.get_tick(settings.SYMBOL)
                await websocket.send_json({
                    "type": "tick",
                    "data": tick
                })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
