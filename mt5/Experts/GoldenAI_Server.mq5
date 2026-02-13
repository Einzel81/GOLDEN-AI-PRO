//+------------------------------------------------------------------+
//| Golden-AI Pro ZMQ Server EA                                      |
//| متقدم لاستقبال أوامر التداول من Python عبر ZeroMQ               |
//+------------------------------------------------------------------+
#property copyright "Golden-AI Pro"
#property link      ""
#property version   "3.00"
#property strict

#include <Zmq/Zmq.mqh>

// Input parameters
input string   Host = "127.0.0.1";
input int      Port = 15555;
input int      MagicNumber = 123456;
input bool     EnableDebug = true;

// Global variables
Context context;
Socket socket(context, ZMQ_REP);
string address;
bool isRunning = false;

//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize ZeroMQ
   address = "tcp://" + Host + ":" + IntegerToString(Port);
   
   if(socket.bind(address) == -1)
   {
      Alert("Failed to bind ZMQ socket to ", address);
      return(INIT_FAILED);
   }
   
   isRunning = true;
   Print("╔════════════════════════════════════════╗");
   Print("║     Golden-AI Pro ZMQ Server v3.0      ║");
   Print("╠════════════════════════════════════════╣");
   Print("║ Status: RUNNING                        ║");
   Print("║ Address: ", address, "                 ║");
   Print("║ Magic: ", IntegerToString(MagicNumber), "                    ║");
   Print("╚════════════════════════════════════════╝");
   
   // Start timer for message processing
   EventSetMillisecondTimer(10);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   isRunning = false;
   EventKillTimer();
   socket.unbind(address);
   socket.close();
   context.destroy();
   
   Print("Golden-AI Pro ZMQ Server stopped");
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(!isRunning) return;
   
   string request;
   int result = socket.recv(request, ZMQ_DONTWAIT);
   
   if(result > 0)
   {
      if(EnableDebug) Print("Received: ", request);
      
      string response = ProcessRequest(request);
      
      if(EnableDebug) Print("Sending: ", response);
      
      socket.send(response);
   }
}

//+------------------------------------------------------------------+
string ProcessRequest(string json_request)
{
   JSONParser parser;
   JSONValue *root = parser.parse(json_request);
   
   if(root == NULL)
      return CreateErrorResponse("Invalid JSON format");
   
   JSONObject *obj = root;
   string action = obj.getString("action");
   
   string response = "{}";
   
   try
   {
      if(action == "GET_RATES")
         response = HandleGetRates(obj);
      else if(action == "GET_TICK")
         response = HandleGetTick(obj);
      else if(action == "TRADE")
         response = HandleTrade(obj);
      else if(action == "CLOSE")
         response = HandleClose(obj);
      else if(action == "CLOSE_ALL")
         response = HandleCloseAll(obj);
      else if(action == "GET_POSITIONS")
         response = HandleGetPositions();
      else if(action == "GET_ORDERS")
         response = HandleGetOrders();
      else if(action == "GET_ACCOUNT")
         response = HandleGetAccount();
      else if(action == "GET_HISTORY")
         response = HandleGetHistory(obj);
      else if(action == "MODIFY")
         response = HandleModify(obj);
      else if(action == "PARTIAL_CLOSE")
         response = HandlePartialClose(obj);
      else
         response = CreateErrorResponse("Unknown action: " + action);
   }
   catch(int err)
   {
      response = CreateErrorResponse("Error: " + IntegerToString(err));
   }
   
   delete root;
   return response;
}

//+------------------------------------------------------------------+
string HandleGetRates(JSONObject *obj)
{
   string symbol = obj.getString("symbol");
   string timeframe = obj.getString("timeframe");
   int count = obj.getInt("count");
   
   ENUM_TIMEFRAMES tf = StringToTimeFrame(timeframe);
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(symbol, tf, 0, count, rates);
   
   if(copied <= 0)
      return CreateErrorResponse("Failed to copy rates");
   
   string json = "{\"status\":\"success\",\"symbol\":\"" + symbol + "\",\"timeframe\":\"" + timeframe + "\",\"data\":[";
   
   for(int i = 0; i < copied; i++)
   {
      if(i > 0) json += ",";
      json += "{";
      json += "\"time\":" + IntegerToString(rates[i].time) + ",";
      json += "\"open\":" + DoubleToString(rates[i].open, 5) + ",";
      json += "\"high\":" + DoubleToString(rates[i].high, 5) + ",";
      json += "\"low\":" + DoubleToString(rates[i].low, 5) + ",";
      json += "\"close\":" + DoubleToString(rates[i].close, 5) + ",";
      json += "\"volume\":" + IntegerToString(rates[i].tick_volume) + ",";
      json += "\"spread\":" + IntegerToString(rates[i].spread);
      json += "}";
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
string HandleGetTick(JSONObject *obj)
{
   string symbol = obj.getString("symbol");
   MqlTick tick;
   
   if(!SymbolInfoTick(symbol, tick))
      return CreateErrorResponse("Failed to get tick");
   
   string json = "{\"status\":\"success\",\"data\":{";
   json += "\"time\":" + IntegerToString(tick.time) + ",";
   json += "\"time_msc\":" + IntegerToString(tick.time_msc) + ",";
   json += "\"bid\":" + DoubleToString(tick.bid, 5) + ",";
   json += "\"ask\":" + DoubleToString(tick.ask, 5) + ",";
   json += "\"last\":" + DoubleToString(tick.last, 5) + ",";
   json += "\"volume\":" + IntegerToString(tick.volume) + ",";
   json += "\"flags\":" + IntegerToString(tick.flags);
   json += "}}";
   
   return json;
}

//+------------------------------------------------------------------+
string HandleTrade(JSONObject *obj)
{
   string symbol = obj.getString("symbol");
   string action = obj.getString("action");
   double volume = obj.getDouble("volume");
   double price = obj.getDouble("price");
   double sl = obj.getDouble("sl");
   double tp = obj.getDouble("tp");
   int deviation = obj.has("deviation") ? obj.getInt("deviation") : 10;
   int magic = obj.has("magic") ? obj.getInt("magic") : MagicNumber;
   string comment = obj.has("comment") ? obj.getString("comment") : "Golden-AI";
   
   // Determine order type and price
   ENUM_ORDER_TYPE order_type;
   double order_price;
   
   if(action == "BUY")
   {
      order_type = ORDER_TYPE_BUY;
      order_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
   }
   else if(action == "SELL")
   {
      order_type = ORDER_TYPE_SELL;
      order_price = SymbolInfoDouble(symbol, SYMBOL_BID);
   }
   else if(action == "BUY_LIMIT")
   {
      order_type = ORDER_TYPE_BUY_LIMIT;
      order_price = price;
   }
   else if(action == "SELL_LIMIT")
   {
      order_type = ORDER_TYPE_SELL_LIMIT;
      order_price = price;
   }
   else if(action == "BUY_STOP")
   {
      order_type = ORDER_TYPE_BUY_STOP;
      order_price = price;
   }
   else if(action == "SELL_STOP")
   {
      order_type = ORDER_TYPE_SELL_STOP;
      order_price = price;
   }
   else
      return CreateErrorResponse("Invalid action");
   
   // Fill policy
   ENUM_ORDER_TYPE_FILLING fill_policy = GetFillingMode(symbol);
   
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = order_type;
   request.price = order_price;
   request.sl = sl;
   request.tp = tp;
   request.deviation = deviation;
   request.magic = magic;
   request.comment = comment;
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = fill_policy;
   
   MqlTradeResult result = {};
   if(!OrderSend(request, result))
      return CreateErrorResponse("OrderSend failed: " + IntegerToString(GetLastError()));
   
   string json = "{\"status\":\"success\",\"data\":{";
   json += "\"ticket\":" + IntegerToString(result.order) + ",";
   json += "\"price\":" + DoubleToString(result.price, 5) + ",";
   json += "\"volume\":" + DoubleToString(result.volume, 2) + ",";
   json += "\"retcode\":" + IntegerToString(result.retcode) + ",";
   json += "\"comment\":\"" + result.comment + "\"";
   json += "}}";
   
   return json;
}

//+------------------------------------------------------------------+
string HandleClose(JSONObject *obj)
{
   int ticket = obj.getInt("ticket");
   
   if(!PositionSelectByTicket(ticket))
      return CreateErrorResponse("Position not found");
   
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
   
   ENUM_ORDER_TYPE_FILLING fill_policy = GetFillingMode(symbol);
   
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_DEAL;
   request.symbol = symbol;
   request.volume = volume;
   request.type = order_type;
   request.position = ticket;
   request.price = price;
   request.deviation = 10;
   request.magic = PositionGetInteger(POSITION_MAGIC);
   request.comment = "Golden-AI Close";
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = fill_policy;
   
   MqlTradeResult result = {};
   if(!OrderSend(request, result))
      return CreateErrorResponse("Close failed: " + IntegerToString(GetLastError()));
   
   return "{\"status\":\"success\",\"data\":{\"ticket\":" + IntegerToString(result.order) + "}}";
}

//+------------------------------------------------------------------+
string HandleCloseAll(JSONObject *obj)
{
   int closed = 0;
   int failed = 0;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      // Check if it's our magic number
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      
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
      request.type_filling = GetFillingMode(symbol);
      
      MqlTradeResult result = {};
      if(OrderSend(request, result))
         closed++;
      else
         failed++;
   }
   
   return "{\"status\":\"success\",\"data\":{\"closed\":" + IntegerToString(closed) + 
          ",\"failed\":" + IntegerToString(failed) + "}}";
}

//+------------------------------------------------------------------+
string HandleGetPositions()
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
      json += "\"magic\":" + IntegerToString(PositionGetInteger(POSITION_MAGIC)) + ",";
      json += "\"volume\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + ",";
      json += "\"open_price\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 5) + ",";
      json += "\"current_price\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_CURRENT), 5) + ",";
      json += "\"sl\":" + DoubleToString(PositionGetDouble(POSITION_SL), 5) + ",";
      json += "\"tp\":" + DoubleToString(PositionGetDouble(POSITION_TP), 5) + ",";
      json += "\"swap\":" + DoubleToString(PositionGetDouble(POSITION_SWAP), 2) + ",";
      json += "\"profit\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2) + ",";
      json += "\"comment\":\"" + PositionGetString(POSITION_COMMENT) + "\"";
      json += "}";
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
string HandleGetOrders()
{
   string json = "{\"status\":\"success\",\"data\":[";
   
   for(int i = 0; i < OrdersTotal(); i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket <= 0) continue;
      
      if(i > 0) json += ",";
      json += "{";
      json += "\"ticket\":" + IntegerToString(ticket) + ",";
      json += "\"symbol\":\"" + OrderGetString(ORDER_SYMBOL) + "\",";
      json += "\"type\":" + IntegerToString(OrderGetInteger(ORDER_TYPE)) + ",";
      json += "\"state\":" + IntegerToString(OrderGetInteger(ORDER_STATE)) + ",";
      json += "\"volume\":" + DoubleToString(OrderGetDouble(ORDER_VOLUME_CURRENT), 2) + ",";
      json += "\"price\":" + DoubleToString(OrderGetDouble(ORDER_PRICE_OPEN), 5) + ",";
      json += "\"sl\":" + DoubleToString(OrderGetDouble(ORDER_SL), 5) + ",";
      json += "\"tp\":" + DoubleToString(OrderGetDouble(ORDER_TP), 5);
      json += "}";
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
string HandleGetAccount()
{
   string json = "{\"status\":\"success\",\"data\":{";
   json += "\"number\":" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + ",";
   json += "\"name\":\"" + AccountInfoString(ACCOUNT_NAME) + "\",";
   json += "\"server\":\"" + AccountInfoString(ACCOUNT_SERVER) + "\",";
   json += "\"currency\":\"" + AccountInfoString(ACCOUNT_CURRENCY) + "\",";
   json += "\"leverage\":" + IntegerToString(AccountInfoInteger(ACCOUNT_LEVERAGE)) + ",";
   json += "\"balance\":" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",";
   json += "\"equity\":" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + ",";
   json += "\"margin\":" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN), 2) + ",";
   json += "\"free_margin\":" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2) + ",";
   json += "\"margin_level\":" + DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_LEVEL), 2) + ",";
   json += "\"profit\":" + DoubleToString(AccountInfoDouble(ACCOUNT_PROFIT), 2);
   json += "}}";
   
   return json;
}

//+------------------------------------------------------------------+
string HandleGetHistory(JSONObject *obj)
{
   datetime from_date = obj.has("from") ? obj.getInt("from") : 0;
   datetime to_date = obj.has("to") ? obj.getInt("to") : TimeCurrent();
   
   HistorySelect(from_date, to_date);
   
   string json = "{\"status\":\"success\",\"data\":[";
   
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket <= 0) continue;
      
      if(i > 0) json += ",";
      json += "{";
      json += "\"ticket\":" + IntegerToString(ticket) + ",";
      json += "\"symbol\":\"" + HistoryDealGetString(ticket, DEAL_SYMBOL) + "\",";
      json += "\"type\":" + IntegerToString(HistoryDealGetInteger(ticket, DEAL_TYPE)) + ",";
      json += "\"entry\":" + IntegerToString(HistoryDealGetInteger(ticket, DEAL_ENTRY)) + ",";
      json += "\"volume\":" + DoubleToString(HistoryDealGetDouble(ticket, DEAL_VOLUME), 2) + ",";
      json += "\"price\":" + DoubleToString(HistoryDealGetDouble(ticket, DEAL_PRICE), 5) + ",";
      json += "\"profit\":" + DoubleToString(HistoryDealGetDouble(ticket, DEAL_PROFIT), 2) + ",";
      json += "\"time\":" + IntegerToString(HistoryDealGetInteger(ticket, DEAL_TIME));
      json += "}";
   }
   
   json += "]}";
   return json;
}

//+------------------------------------------------------------------+
string HandleModify(JSONObject *obj)
{
   int ticket = obj.getInt("ticket");
   double sl = obj.has("sl") ? obj.getDouble("sl") : 0;
   double tp = obj.has("tp") ? obj.getDouble("tp") : 0;
   
   if(!PositionSelectByTicket(ticket))
      return CreateErrorResponse("Position not found");
   
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.sl = sl;
   request.tp = tp;
   
   MqlTradeResult result = {};
   if(!OrderSend(request, result))
      return CreateErrorResponse("Modify failed: " + IntegerToString(GetLastError()));
   
   return "{\"status\":\"success\",\"data\":{\"ticket\":" + IntegerToString(ticket) + "}}";
}

//+------------------------------------------------------------------+
string HandlePartialClose(JSONObject *obj)
{
   int ticket = obj.getInt("ticket");
   double volume = obj.getDouble("volume");
   
   if(!PositionSelectByTicket(ticket))
      return CreateErrorResponse("Position not found");
   
   string symbol = PositionGetString(POSITION_SYMBOL);
   long pos_type = PositionGetInteger(POSITION_TYPE);
   double pos_volume = PositionGetDouble(POSITION_VOLUME);
   
   if(volume >= pos_volume)
      return CreateErrorResponse("Close volume >= position volume");
   
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
   request.type_filling = GetFillingMode(symbol);
   
   MqlTradeResult result = {};
   if(!OrderSend(request, result))
      return CreateErrorResponse("Partial close failed: " + IntegerToString(GetLastError()));
   
   return "{\"status\":\"success\",\"data\":{\"ticket\":" + IntegerToString(result.order) + 
          ",\"remaining_volume\":" + DoubleToString(pos_volume - volume, 2) + "}}";
}

//+------------------------------------------------------------------+
string CreateErrorResponse(string error)
{
   return "{\"status\":\"error\",\"error\":\"" + error + "\"}";
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
ENUM_ORDER_TYPE_FILLING GetFillingMode(string symbol)
{
   uint filling = (uint)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   
   if((filling & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
   
   if((filling & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   
   return ORDER_FILLING_RETURN;
}
//+------------------------------------------------------------------+
