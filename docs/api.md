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
