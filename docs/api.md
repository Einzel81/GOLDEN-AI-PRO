# Golden-AI Pro API Documentation

## Base URL

http://localhost:8000


## Authentication
All endpoints require API key in header:


## Endpoints

### Health & Status

#### GET `/health`
Check system health status.

**Response:**
```json
{
  "status": "healthy",
  "mt5": {
    "status": "connected",
    "symbol": "XAUUSD",
    "last_tick": "2024-01-15T10:30:00",
    "account_balance": 10000.00
  },
  "timestamp": "Golden-AI Pro"
}


Account
GET /api/v1/account
Get account information.
Response:

{
  "number": 12345678,
  "name": "Trading Account",
  "server": "Broker-Server",
  "currency": "USD",
  "leverage": 100,
  "balance": 10000.00,
  "equity": 10050.00,
  "margin": 500.00,
  "free_margin": 9550.00,
  "profit": 50.00
}


Trading
POST /api/v1/trade
Execute a new trade.
Request:


{
  "action": "buy",
  "volume": 0.1,
  "stop_loss": 1900.00,
  "take_profit": 1920.00
}


Response:


{
  "success": true,
  "order_id": "ORD_20240115_103000_1",
  "ticket": 123456789,
  "status": "filled",
  "price": 1910.50
}

GET /api/v1/positions
Get open positions.
Response:

{
  "positions": [
    {
      "ticket": 123456789,
      "symbol": "XAUUSD",
      "type": 0,
      "volume": 0.1,
      "open_price": 1910.50,
      "current_price": 1915.00,
      "sl": 1900.00,
      "tp": 1920.00,
      "profit": 45.00
    }
  ],
  "count": 1
}

POST /api/v1/close/{order_id}
Close a specific position.
Response:

{
  "success": true,
  "closed_price": 1915.00,
  "profit": 45.00
}

Analysis
POST /api/v1/analyze
Analyze market conditions.
Query Parameters:
timeframe: H1, H4, D1 (default: H1)
Response:

{
  "signal": "buy",
  "confidence": 0.85,
  "entry": 1910.50,
  "stop_loss": 1900.00,
  "take_profit": 1930.00,
  "timeframe": "H1",
  "timestamp": "2024-01-15T10:30:00",
  "components": {
    "order_blocks": 3,
    "fvgs": 2,
    "liquidity_levels": 5
  }
}

Risk Management
GET /api/v1/risk/status
Get current risk status.
Response:

{
  "daily_pnl": 150.00,
  "current_drawdown": 0.02,
  "consecutive_losses": 0,
  "open_trades_limit": 5,
  "trading_allowed": true,
  "risk_parameters": {
    "max_risk_per_trade": 0.02,
    "max_daily_drawdown": 0.05,
    "max_total_drawdown": 0.20
  }
}


WebSocket
Connect to ws://localhost:8000/ws for real-time updates.
Message Format:

{
  "type": "tick",
  "data": {
    "time": "2024-01-15T10:30:00",
    "bid": 1910.45,
    "ask": 1910.55,
    "last": 1910.50
  }
}

Error Codes
Table
Copy
Code	Description
400	Bad Request
401	Unauthorized
403	Forbidden
404	Not Found
500	Internal Server Error
503	Service Unavailable
Rate Limiting
100 requests per minute for standard endpoints
1000 requests per minute for market data


### 9. `docs/architecture.md`

```markdown
# Golden-AI Pro Architecture

## Overview
Golden-AI Pro follows a layered microservices architecture with clear separation of concerns.

## System Architecture
