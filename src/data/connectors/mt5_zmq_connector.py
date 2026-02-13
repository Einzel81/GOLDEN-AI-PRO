"""
موصل MT5 عبر ZeroMQ
MT5 ZeroMQ Connector for remote connections
"""

import zmq
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, asdict
from loguru import logger
import pandas as pd

from config.settings import settings


@dataclass
class ZMQTradeRequest:
    """طلب تداول عبر ZMQ"""
    action: str
    symbol: str
    volume: float
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    deviation: int = 10
    magic: int = 123456
    comment: str = "Golden-AI-ZMQ"


class MT5ZMQConnector:
    """
    موصل MT5 عبر ZeroMQ للاتصال عن بعد
    يتطلب EA خاص على MT5
    """
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.ZMQ_HOST
        self.port = port or settings.ZMQ_PORT
        self.timeout = settings.ZMQ_TIMEOUT
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
        self.socket.setsockopt(zmq.LINGER, 0)
        
        self.connected = False
        self._lock = asyncio.Lock()
        
    async def connect(self) -> bool:
        """الاتصال بـ MT5 عبر ZMQ"""
        try:
            self.socket.connect(f"tcp://{self.host}:{self.port}")
            self.connected = True
            logger.success(f"ZMQ connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"ZMQ connection failed: {e}")
            return False
    
    async def disconnect(self):
        """قطع الاتصال"""
        self.socket.close()
        self.context.term()
        self.connected = False
        logger.info("ZMQ disconnected")
    
    async def _send_command(self, command: Dict) -> Dict:
        """إرسال أمر واستلام الرد"""
        if not self.connected:
            raise Exception("Not connected")
        
        async with self._lock:
            try:
                # Send command
                self.socket.send_json(command)
                
                # Receive response
                response = self.socket.recv_json()
                return response
                
            except zmq.Again:
                logger.error("ZMQ timeout")
                # Reconnect socket
                self.socket.close()
                self.socket = self.context.socket(zmq.REQ)
                self.socket.setsockopt(zmq.RCVTIMEO, self.timeout)
                self.socket.connect(f"tcp://{self.host}:{self.port}")
                raise Exception("ZMQ timeout - reconnected")
            except Exception as e:
                logger.error(f"ZMQ error: {e}")
                raise
    
    async def get_rates(self, symbol: str, timeframe: str, count: int = 1000) -> pd.DataFrame:
        """جلب البيانات التاريخية"""
        command = {
            "action": "GET_RATES",
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count
        }
        
        response = await self._send_command(command)
        
        if response.get("status") != "success":
            raise Exception(response.get("error", "Unknown error"))
        
        data = response.get("data", [])
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        return df
    
    async def get_tick(self, symbol: str) -> Dict:
        """جلب آخر سعر"""
        command = {
            "action": "GET_TICK",
            "symbol": symbol
        }
        
        response = await self._send_command(command)
        return response.get("data", {})
    
    async def execute_trade(self, request: ZMQTradeRequest) -> Dict:
        """تنفيذ صفقة"""
        command = {
            "action": "TRADE",
            **asdict(request)
        }
        
        response = await self._send_command(command)
        return response
    
    async def close_position(self, ticket: int) -> Dict:
        """إغلاق مركز"""
        command = {
            "action": "CLOSE",
            "ticket": ticket
        }
        
        response = await self._send_command(command)
        return response
    
    async def get_positions(self) -> List[Dict]:
        """جلب المراكز"""
        command = {"action": "GET_POSITIONS"}
        response = await self._send_command(command)
        return response.get("data", [])
    
    async def get_account_info(self) -> Dict:
        """جلب معلومات الحساب"""
        command = {"action": "GET_ACCOUNT"}
        response = await self._send_command(command)
        return response.get("data", {})
    
    async def subscribe_market_data(self, symbols: List[str]):
        """الاشتراك في بيانات السوق"""
        command = {
            "action": "SUBSCRIBE",
            "symbols": symbols
        }
        response = await self._send_command(command)
        return response.get("status") == "success"


# MQL5 EA Template (GoldenAI_Server.mq5) - يحفظ في mt5/Experts/
MQL5_EA_TEMPLATE = '''
//+------------------------------------------------------------------+
//| Golden-AI ZMQ Server EA                                          |
//+------------------------------------------------------------------+
#property copyright "Golden-AI"
#property link      ""
#property version   "2.00"
#property strict

#include <Zmq/Zmq.mqh>

// Input parameters
input string   Host = "127.0.0.1";
input int      Port = 15555;
input int      MagicNumber = 123456;

// Global variables
Context context;
Socket socket(context, ZMQ_REP);
string address;

//+------------------------------------------------------------------+
int OnInit()
{
   address = "tcp://" + Host + ":" + IntegerToString(Port);
   
   if(socket.bind(address) == -1)
   {
      Print("Failed to bind ZMQ socket");
      return(INIT_FAILED);
   }
   
   Print("Golden-AI ZMQ Server started on ", address);
   EventSetMillisecondTimer(1);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   socket.unbind(address);
   Print("Golden-AI ZMQ Server stopped");
}

//+------------------------------------------------------------------+
void OnTimer()
{
   string request;
   int result = socket.recv(request, ZMQ_DONTWAIT);
   
   if(result > 0)
   {
      string response = ProcessRequest(request);
      socket.send(response);
   }
}

//+------------------------------------------------------------------+
string ProcessRequest(string json_request)
{
   JSONParser parser;
   JSONValue *root = parser.parse(json_request);
   
   if(root == NULL)
      return "{\"status\":\"error\",\"error\":\"Invalid JSON\"}";
   
   JSONObject *obj = root;
   string action = obj.getString("action");
   
   string response = "{}";
   
   if(action == "GET_RATES")
   {
      response = GetRates(obj);
   }
   else if(action == "GET_TICK")
   {
      response = GetTick(obj);
   }
   else if(action == "TRADE")
   {
      response = ExecuteTrade(obj);
   }
   else if(action == "CLOSE")
   {
      response = ClosePosition(obj);
   }
   else if(action == "GET_POSITIONS")
   {
      response = GetPositions();
   }
   else if(action == "GET_ACCOUNT")
   {
      response = GetAccountInfo();
   }
   else if(action == "SUBSCRIBE")
   {
      response = SubscribeSymbols(obj);
   }
   
   delete root;
   return response;
}

//+------------------------------------------------------------------+
string GetRates(JSONObject *obj)
{
   string symbol = obj.getString("symbol");
   string timeframe = obj.getString("timeframe");
   int count = obj.getInt("count");
   
   ENUM_TIMEFRAMES tf = StringToTimeFrame(timeframe);
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, count, rates);
   
   if(copied <= 0)
      return "{\"status\":\"error\",\"error\":\"Failed to copy rates\"}";
   
   string json = "{\"status\":\"success\",\"data\":[";
   
   for(int i = 0; i < copied; i++)
   {
      if(i > 0) json += ",";
      json += "{";
      json += "\"time\":" + IntegerToString(rates[i].time) + ",";
      json += "\"open\":" + DoubleToString(rates[i].open) + ",";
      json += "\"high\":" + DoubleToString(rates[i].high) + ",";
      json += "\"low\":" + DoubleToString(rates[i].low) + ",";
      json += "\"close\":" + DoubleToString(rates[i].close) + ",";
      json += "\"volume\":" + IntegerToString(rates[i].tick_volume);
      json += "}";
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
string GetTick(JSONObject *obj)
{
   string symbol = obj.getString("symbol");
   MqlTick tick;
   
   if(!SymbolInfoTick(symbol, tick))
      return "{\"status\":\"error\",\"error\":\"Failed to get tick\"}";
   
   string json = "{\"status\":\"success\",\"data\":{";
   json += "\"time\":" + IntegerToString(tick.time) + ",";
   json += "\"bid\":" + DoubleToString(tick.bid) + ",";
   json += "\"ask\":" + DoubleToString(tick.ask) + ",";
   json += "\"last\":" + DoubleToString(tick.last) + ",";
   json += "\"volume\":" + IntegerToString(tick.volume);
   json += "}}";
   
   return json;
}

//+------------------------------------------------------------------+
string ExecuteTrade(JSONObject *obj)
{
   string symbol = obj.getString("symbol");
   string action = obj.getString("action");
   double volume = obj.getDouble("volume");
   double price = obj.getDouble("price");
   double sl = obj.getDouble("sl");
   double tp = obj.getDouble("tp");
   int deviation = obj.getInt("deviation");
   int magic = obj.getInt("magic");
   string comment = obj.getString("comment");
   
   ENUM_ORDER_TYPE order_type;
   if(action == "BUY") order_type = ORDER_TYPE_BUY;
   else if(action == "SELL") order_type = ORDER_TYPE_SELL;
   else if(action == "BUY_LIMIT") order_type = ORDER_TYPE_BUY_LIMIT;
   else if(action == "SELL_LIMIT") order_type = ORDER_TYPE_SELL_LIMIT;
   else return "{\"status\":\"error\",\"error\":\"Invalid action\"}";
   
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = order_type;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.deviation = deviation;
   request.magic = magic;
   request.comment = comment;
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_IOC;
   
   MqlTradeResult result = {};
   if(!OrderSend(request, result))
      return "{\"status\":\"error\",\"error\":\"OrderSend failed\"}";
   
   string json = "{\"status\":\"success\",\"data\":{";
   json += "\"ticket\":" + IntegerToString(result.order) + ",";
   json += "\"price\":" + DoubleToString(result.price) + ",";
   json += "\"retcode\":" + IntegerToString(result.retcode);
   json += "}}";
   
   return json;
}

//+------------------------------------------------------------------+
string ClosePosition(JSONObject *obj)
{
   int ticket = obj.getInt("ticket");
   
   if(!PositionSelectByTicket(ticket))
      return "{\"status\":\"error\",\"error\":\"Position not found\"}";
   
   string symbol = PositionGetString(POSITION_SYMBOL);
   long pos_type = PositionGetInteger(POSITION_TYPE);
   double volume = PositionGetDouble(POSITION_VOLUME);
   
   ENUM_ORDER_TYPE order_type;
   double price;
   
   if(pos_type == POSITION_TYPE_BUY)
   {
      order_type = ORDER_TYPE_SELL;
      price = SymbolInfoDouble(symbol, SYMBOL_BID);
   }
   else
   {
      order_type = ORDER_TYPE_BUY;
      price = SymbolInfoDouble(symbol, SYMBOL_ASK);
   }
   
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = order_type;
   request.position = ticket;
   request.price = price;
   request.deviation = 10;
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_IOC;
   
   MqlTradeResult result = {};
   if(!OrderSend(request, result))
      return "{\"status\":\"error\",\"error\":\"Close failed\"}";
   
   return "{\"status\":\"success\",\"data\":{\"ticket\":" + IntegerToString(result.order) + "}}";
}

//+------------------------------------------------------------------+
string GetPositions()
{
   string json = "{\"status\":\"success\",\"data\":[";
   
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      if(i > 0) json += ",";
      json += "{";
      json += "\"ticket\":" + IntegerToString(ticket) + ",";
      json += "\"symbol\":\"" + PositionGetString(POSITION_SYMBOL) + "\",";
      json += "\"type\":" + IntegerToString(PositionGetInteger(POSITION_TYPE)) + ",";
      json += "\"volume\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME)) + ",";
      json += "\"open_price\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN)) + ",";
      json += "\"sl\":" + DoubleToString(PositionGetDouble(POSITION_SL)) + ",";
      json += "\"tp\":" + DoubleToString(PositionGetDouble(POSITION_TP)) + ",";
      json += "\"profit\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT));
      json += "}";
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
string GetAccountInfo()
{
   string json = "{\"status\":\"success\",\"data\":{";
   json += "\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE)) + ",";
   json += "\"equity\":" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY)) + ",";
   json += "\"margin\":" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN)) + ",";
   json += "\"free_margin\":" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE)) + ",";
   json += "\"leverage\":" + IntegerToString(AccountInfoInteger(ACCOUNT_LEVERAGE)) + ",";
   json += "\"currency\":\"" + AccountInfoString(ACCOUNT_CURRENCY) + "\"";
   json += "}}";
   
   return json;
}

//+------------------------------------------------------------------+
string SubscribeSymbols(JSONObject *obj)
{
   // Implementation for market data subscription
   return "{\"status\":\"success\"}";
}

//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTimeFrame(string tf)
{
   if(tf == "M1") return PERIOD_M1;
   if(tf == "M5") return PERIOD_M5;
   if(tf == "M15") return PERIOD_M15;
   if(tf == "M30") return PERIOD_M30;
   if(tf == "H1") return PERIOD_H1;
   if(tf == "H4") return PERIOD_H4;
   if(tf == "D1") return PERIOD_D1;
   if(tf == "W1") return PERIOD_W1;
   if(tf == "MN1") return PERIOD_MN1;
   return PERIOD_CURRENT;
}
//+------------------------------------------------------------------+
'''
