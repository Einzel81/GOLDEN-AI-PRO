"""
مدير الأوامر المتقدم
Advanced Order Management with smart execution
"""

import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from src.data.connectors.mt5_connector import MT5Connector, TradeRequest, TradeResult
from src.risk.risk_manager import RiskManager


@dataclass
class Order:
    """أمر تداول"""
    id: str
    symbol: str
    action: str  # buy, sell
    volume: float
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    order_type: str  # market, limit, stop
    status: str  # pending, filled, cancelled, closed
    created_at: datetime
    filled_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    ticket: Optional[int] = None
    pnl: Optional[float] = None


class OrderManager:
    """
    مدير أوامر ذكي يتضمن:
    - تنفيذ ذكي للأوامر
    - إدارة الأوامر المعلقة
    - تتبع الأوامر المفتوحة
    - إدارة SL/TP الديناميكية
    """
    
    def __init__(self, mt5_connector: MT5Connector, risk_manager: RiskManager):
        self.mt5 = mt5_connector
        self.risk = risk_manager
        self.orders: Dict[str, Order] = {}
        self.pending_orders: List[Order] = []
        self.position_tracking: Dict[int, Dict] = {}
        
    async def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        order_type: str = "market",
        deviation: int = 10
    ) -> Order:
        """
        وضع أمر جديد
        """
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.orders)}"
        
        order = Order(
            id=order_id,
            symbol=symbol,
            action=action,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_type=order_type,
            status="pending",
            created_at=datetime.now()
        )
        
        # تنفيذ الأمر
        if order_type == "market":
            result = await self._execute_market_order(order, deviation)
        else:
            result = await self._execute_pending_order(order)
        
        if result.success:
            order.status = "filled"
            order.filled_at = datetime.now()
            order.ticket = result.ticket
            logger.success(f"Order {order_id} filled | Ticket: {result.ticket}")
        else:
            order.status = "failed"
            logger.error(f"Order {order_id} failed: {result.error}")
        
        self.orders[order_id] = order
        return order
    
    async def _execute_market_order(self, order: Order, deviation: int) -> TradeResult:
        """تنفيذ أمر سوقي"""
        request = TradeRequest(
            action=order.action.upper(),
            symbol=order.symbol,
            volume=order.volume,
            sl=order.stop_loss,
            tp=order.take_profit,
            deviation=deviation
        )
        
        return await self.mt5.execute_trade(request)
    
    async def _execute_pending_order(self, order: Order) -> TradeResult:
        """تنفيذ أمر معلق"""
        # تحويل إلى نوع MT5 المناسب
        action_map = {
            'buy': 'BUY_LIMIT' if order.entry_price < await self._get_current_price(order.symbol, 'ask') else 'BUY_STOP',
            'sell': 'SELL_LIMIT' if order.entry_price > await self._get_current_price(order.symbol, 'bid') else 'SELL_STOP'
        }
        
        request = TradeRequest(
            action=action_map.get(order.action, 'BUY'),
            symbol=order.symbol,
            volume=order.volume,
            price=order.entry_price,
            sl=order.stop_loss,
            tp=order.take_profit
        )
        
        return await self.mt5.execute_trade(request)
    
    async def _get_current_price(self, symbol: str, price_type: str) -> float:
        """جلب السعر الحالي"""
        tick = await self.mt5.get_tick(symbol)
        return tick.get(price_type, 0)
    
    async def close_position(self, order_id: str, partial: Optional[float] = None) -> bool:
        """إغلاق مركز"""
        order = self.orders.get(order_id)
        if not order or not order.ticket:
            logger.error(f"Order {order_id} not found or not filled")
            return False
        
        # إغلاق كلي أو جزئي
        if partial and partial < order.volume:
            # تنفيذ إغلاق جزئي (يتطلب تعديل الحجم)
            new_volume = order.volume - partial
            # Note: MT5 doesn't support partial close directly, need to open opposite position
            logger.info(f"Partial close not implemented, closing full position")
        
        result = await self.mt5.close_position(order.ticket)
        
        if result.success:
            order.status = "closed"
            order.closed_at = datetime.now()
            logger.success(f"Position {order_id} closed")
            return True
        
        logger.error(f"Failed to close position {order_id}: {result.error}")
        return False
    
    async def modify_order(
        self,
        order_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> bool:
        """تعديل أمر"""
        order = self.orders.get(order_id)
        if not order or not order.ticket:
            return False
        
        success = await self.mt5.modify_position(order.ticket, stop_loss, take_profit)
        
        if success:
            if stop_loss:
                order.stop_loss = stop_loss
            if take_profit:
                order.take_profit = take_profit
            logger.info(f"Order {order_id} modified | SL: {stop_loss} | TP: {take_profit}")
        
        return success
    
    async def update_trailing_stop(self, order_id: str, activation_pips: float, distance_pips: float):
        """تحديث وقف الخسارة المتحرك"""
        order = self.orders.get(order_id)
        if not order or not order.ticket:
            return
        
        # جلب السعر الحالي
        tick = await self.mt5.get_tick(order.symbol)
        current_price = tick['bid'] if order.action == 'buy' else tick['ask']
        
        # حساب الربح الحالي بالنقاط
        if order.action == 'buy':
            profit_pips = (current_price - order.entry_price) / 0.01  # XAUUSD
        else:
            profit_pips = (order.entry_price - current_price) / 0.01
        
        # تفعيل الـ trailing stop
        if profit_pips >= activation_pips:
            new_sl = current_price - (distance_pips * 0.01) if order.action == 'buy' else current_price + (distance_pips * 0.01)
            
            # التأكد من أن SL الجديد أفضل من الحالي
            if order.action == 'buy' and (order.stop_loss is None or new_sl > order.stop_loss):
                await self.modify_order(order_id, stop_loss=new_sl)
            elif order.action == 'sell' and (order.stop_loss is None or new_sl < order.stop_loss):
                await self.modify_order(order_id, stop_loss=new_sl)
    
    async def sync_positions(self):
        """مزامنة المراكز مع MT5"""
        positions = await self.mt5.get_positions()
        
        # تحديث حالة الأوامر المحلية
        open_tickets = {p['ticket'] for p in positions}
        
        for order in self.orders.values():
            if order.status == "filled" and order.ticket not in open_tickets:
                # المركز مغلق في MT5
                order.status = "closed"
                order.closed_at = datetime.now()
                logger.info(f"Order {order.id} marked as closed (synced with MT5)")
        
        return positions
    
    async def get_open_orders(self) -> List[Order]:
        """جلب الأوامر المفتوحة"""
        return [o for o in self.orders.values() if o.status == "filled"]
    
    async def get_order_history(self, limit: int = 100) -> List[Order]:
        """جلب سجل الأوامر"""
        sorted_orders = sorted(
            self.orders.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return sorted_orders[:limit]
    
    async def cancel_pending_order(self, order_id: str) -> bool:
        """إلغاء أمر معلق"""
        # Note: Requires implementation in MT5 connector
        logger.info(f"Cancelling pending order {order_id}")
        return True
    
    def get_position_exposure(self) -> Dict:
        """حساب التعرض الإجمالي"""
        exposure = {'buy': 0, 'sell': 0}
        
        for order in self.orders.values():
            if order.status == "filled":
                exposure[order.action] += order.volume
        
        net_exposure = exposure['buy'] - exposure['sell']
        
        return {
            'buy_volume': exposure['buy'],
            'sell_volume': exposure['sell'],
            'net_exposure': net_exposure,
            'total_volume': exposure['buy'] + exposure['sell']
        }
