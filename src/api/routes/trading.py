"""
مسارات التداول
Trading Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.execution.order_manager import order_manager
from src.risk.risk_manager import risk_manager
from src.data.connectors.mt5_connector import mt5_connector
from config.settings import settings

router = APIRouter(prefix="/trading", tags=["trading"])


class TradeRequest(BaseModel):
    action: str  # buy, sell
    volume: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_type: str = "market"  # market, limit, stop


@router.post("/execute")
async def execute_trade(request: TradeRequest):
    """
    تنفيذ صفقة
    """
    try:
        # التحقق من المخاطر
        account_info = await mt5_connector.get_account_info()
        open_positions = await mt5_connector.get_positions()
        
        if not risk_manager.check_trade_allowed(account_info['balance'], len(open_positions)):
            raise HTTPException(status_code=400, detail="Trading not allowed due to risk limits")
        
        # تنفيذ الأمر
        order = await order_manager.place_order(
            symbol=settings.SYMBOL,
            action=request.action,
            volume=request.volume,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            order_type=request.order_type
        )
        
        return {
            "success": order.status == "filled",
            "order_id": order.id,
            "ticket": order.ticket,
            "status": order.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close/{order_id}")
async def close_position(order_id: str, partial: Optional[float] = None):
    """
    إغلاق مركز
    """
    try:
        success = await order_manager.close_position(order_id, partial)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modify/{order_id}")
async def modify_position(
    order_id: str,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
):
    """
    تعديل مركز (SL/TP)
    """
    try:
        success = await order_manager.modify_order(order_id, stop_loss, take_profit)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions():
    """
    الحصول على المراكز المفتوحة
    """
    try:
        positions = await order_manager.get_open_orders()
        return {
            "positions": [
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "action": p.action,
                    "volume": p.volume,
                    "entry_price": p.entry_price,
                    "current_price": p.entry_price,  # يمكن تحديثه
                    "stop_loss": p.stop_loss,
                    "take_profit": p.take_profit,
                    "status": p.status
                }
                for p in positions
            ],
            "count": len(positions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
