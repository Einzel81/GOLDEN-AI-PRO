"""
موصل MetaTrader 5 المتقدم
Advanced MetaTrader 5 Connector
"""

import asyncio
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass
from loguru import logger
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings


@dataclass
class TradeRequest:
    """طلب تداول"""
    action: str  # BUY, SELL, CLOSE, MODIFY
    symbol: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 10
    magic: int = 123456
    comment: str = "Golden-AI"
    ticket: Optional[int] = None


@dataclass
class TradeResult:
    """نتيجة التداول"""
    success: bool
    ticket: Optional[int]
    price: Optional[float]
    error: Optional[str]
    request: TradeRequest


class MT5Connector:
    """
    موصل متقدد لـ MetaTrader 5 مع إدارة حالة وإعادة اتصال تلقائية
    """
    
    def __init__(self):
        self.connected: bool = False
        self.account_info: Optional[Dict] = None
        self.symbols_info: Dict[str, Dict] = {}
        self._price_callbacks: List[Callable] = []
        self._connection_lock = asyncio.Lock()
        self._last_error: Optional[str] = None
        
    async def connect(self) -> bool:
        """الاتصال بـ MT5"""
        async with self._connection_lock:
            try:
                if self.connected:
                    return True
                
                # Initialize MT5
                if not mt5.initialize(
                    path=settings.MT5_PATH,
                    login=settings.MT5_ACCOUNT,
                    password=settings.MT5_PASSWORD,
                    server=settings.MT5_SERVER
                ):
                    self._last_error = mt5.last_error()
                    logger.error(f"MT5 initialization failed: {self._last_error}")
                    return False
                
                # Login if credentials provided
                if settings.MT5_ACCOUNT and settings.MT5_PASSWORD:
                    authorized = mt5.login(
                        login=settings.MT5_ACCOUNT,
                        password=settings.MT5_PASSWORD,
                        server=settings.MT5_SERVER
                    )
                    if not authorized:
                        self._last_error = "Login failed"
                        logger.error("MT5 login failed")
                        mt5.shutdown()
                        return False
                
                self.connected = True
                self.account_info = mt5.account_info()._asdict()
                
                logger.success(f"Connected to MT5 | Account: {self.account_info['name']} | Balance: {self.account_info['balance']}")
                return True
                
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"MT5 connection error: {e}")
                return False
    
    async def disconnect(self):
        """قطع الاتصال"""
        async with self._connection_lock:
            if self.connected:
                mt5.shutdown()
                self.connected = False
                logger.info("Disconnected from MT5")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_rates(self, symbol: str, timeframe: str, count: int = 1000) -> pd.DataFrame:
        """جلب بيانات الأسعار"""
        if not self.connected:
            await self.connect()
        
        # Convert timeframe string to MT5 constant
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1
        }
        
        mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
            if rates is None:
                raise Exception(f"Failed to get rates: {mt5.last_error()}")
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.rename(columns={
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
                'spread': 'spread',
                'real_volume': 'real_volume'
            }, inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching rates: {e}")
            raise
    
    async def get_tick(self, symbol: str) -> Dict:
        """جلب آخر tick"""
        if not self.connected:
            await self.connect()
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise Exception(f"Failed to get tick: {mt5.last_error()}")
        
        return {
            'time': datetime.fromtimestamp(tick.time),
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume,
            'time_msc': tick.time_msc,
            'flags': tick.flags
        }
    
    async def get_symbol_info(self, symbol: str) -> Dict:
        """جلب معلومات الرمز"""
        if not self.connected:
            await self.connect()
        
        info = mt5.symbol_info(symbol)
        if info is None:
            raise Exception(f"Symbol not found: {symbol}")
        
        return {
            'name': info.name,
            'description': info.description,
            'currency_base': info.currency_base,
            'currency_profit': info.currency_profit,
            'currency_margin': info.currency_margin,
            'digits': info.digits,
            'point': info.point,
            'trade_tick_size': info.trade_tick_size,
            'trade_tick_value': info.trade_tick_value,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'spread': info.spread,
            'trade_stops_level': info.trade_stops_level
        }
    
    async def execute_trade(self, request: TradeRequest) -> TradeResult:
        """تنفيذ صفقة"""
        if not self.connected:
            await self.connect()
        
        try:
            # Prepare order
            symbol_info = await self.get_symbol_info(request.symbol)
            
            # Determine order type
            if request.action == "BUY":
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(request.symbol).ask
            elif request.action == "SELL":
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(request.symbol).bid
            elif request.action == "BUY_LIMIT":
                order_type = mt5.ORDER_TYPE_BUY_LIMIT
                price = request.price
            elif request.action == "SELL_LIMIT":
                order_type = mt5.ORDER_TYPE_SELL_LIMIT
                price = request.price
            else:
                raise ValueError(f"Unknown action: {request.action}")
            
            # Build request
            mt5_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": request.symbol,
                "volume": float(request.volume),
                "type": order_type,
                "price": price,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add SL/TP if provided
            if request.sl:
                mt5_request["sl"] = request.sl
            if request.tp:
                mt5_request["tp"] = request.tp
            
            # Send order
            result = mt5.order_send(mt5_request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.success(f"Trade executed | Ticket: {result.order} | {request.action} {request.volume} {request.symbol}")
                return TradeResult(
                    success=True,
                    ticket=result.order,
                    price=result.price,
                    error=None,
                    request=request
                )
            else:
                error_msg = f"Trade failed: {result.retcode} - {result.comment}"
                logger.error(error_msg)
                return TradeResult(
                    success=False,
                    ticket=None,
                    price=None,
                    error=error_msg,
                    request=request
                )
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return TradeResult(
                success=False,
                ticket=None,
                price=None,
                error=str(e),
                request=request
            )
    
    async def close_position(self, ticket: int, deviation: int = 10) -> TradeResult:
        """إغلاق مركز"""
        if not self.connected:
            await self.connect()
        
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return TradeResult(
                    success=False,
                    ticket=None,
                    price=None,
                    error="Position not found",
                    request=None
                )
            
            pos = position[0]
            
            # Determine close price
            symbol_info = mt5.symbol_info(pos.symbol)
            if pos.type == mt5.ORDER_TYPE_BUY:
                price = symbol_info.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:
                price = symbol_info.ask
                order_type = mt5.ORDER_TYPE_BUY
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": deviation,
                "magic": pos.magic,
                "comment": "Golden-AI Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(close_request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.success(f"Position closed | Ticket: {ticket}")
                return TradeResult(
                    success=True,
                    ticket=result.order,
                    price=result.price,
                    error=None,
                    request=None
                )
            else:
                error_msg = f"Close failed: {result.retcode} - {result.comment}"
                logger.error(error_msg)
                return TradeResult(
                    success=False,
                    ticket=None,
                    price=None,
                    error=error_msg,
                    request=None
                )
                
        except Exception as e:
            logger.error(f"Close position error: {e}")
            return TradeResult(
                success=False,
                ticket=None,
                price=None,
                error=str(e),
                request=None
            )
    
    async def modify_position(self, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> bool:
        """تعديل مركز (SL/TP)"""
        if not self.connected:
            await self.connect()
        
        try:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
            }
            
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position modified | Ticket: {ticket} | SL: {sl} | TP: {tp}")
                return True
            else:
                logger.error(f"Modify failed: {result.retcode}")
                return False
                
        except Exception as e:
            logger.error(f"Modify position error: {e}")
            return False
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """جلب المراكز المفتوحة"""
        if not self.connected:
            await self.connect()
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if positions is None:
            return []
        
        return [pos._asdict() for pos in positions]
    
    async def get_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """جلب الأوامر المعلقة"""
        if not self.connected:
            await self.connect()
        
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()
        
        if orders is None:
            return []
        
        return [order._asdict() for order in orders]
    
    async def get_account_info(self) -> Dict:
        """جلب معلومات الحساب"""
        if not self.connected:
            await self.connect()
        
        info = mt5.account_info()
        if info is None:
            raise Exception("Failed to get account info")
        
        return info._asdict()
    
    async def get_terminal_info(self) -> Dict:
        """جلب معلومات المحطة"""
        if not self.connected:
            await self.connect()
        
        info = mt5.terminal_info()
        if info is None:
            raise Exception("Failed to get terminal info")
        
        return info._asdict()
    
    def subscribe_to_ticks(self, symbol: str, callback: Callable):
        """الاشتراك في تحديثات الأسعار"""
        self._price_callbacks.append(callback)
        # Note: Real-time tick streaming requires additional implementation
        logger.info(f"Subscribed to ticks for {symbol}")
    
    async def health_check(self) -> Dict:
        """فحص صحة الاتصال"""
        if not self.connected:
            return {"status": "disconnected", "error": self._last_error}
        
        try:
            tick = mt5.symbol_info_tick(settings.SYMBOL)
            account = mt5.account_info()
            
            return {
                "status": "connected",
                "symbol": settings.SYMBOL,
                "last_tick": tick.time if tick else None,
                "account_balance": account.balance if account else None,
                "open_positions": len(mt5.positions_get()) if account else 0
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton instance
mt5_connector = MT5Connector()
