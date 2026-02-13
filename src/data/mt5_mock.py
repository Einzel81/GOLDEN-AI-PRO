"""
محاكاة MetaTrader5 لنظام Linux
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


class MockMT5:
    """
    محاكاة MT5 للاختبار على Linux
    """
    
    def __init__(self):
        self.connected = False
        self.account_info = {
            'login': 123456,
            'balance': 10000.0,
            'equity': 10000.0,
            'margin': 0.0
        }
    
    def initialize(self, path=None):
        """محاكاة الاتصال"""
        self.connected = True
        print("✅ [MOCK] MT5 Initialized (Linux Mode)")
        return True
    
    def shutdown(self):
        """محاكاة الإغلاق"""
        self.connected = False
        print("🔌 [MOCK] MT5 Shutdown")
    
    def login(self, login, password, server):
        """محاكاة تسجيل الدخول"""
        return True
    
    def account_info(self):
        """معلومات الحساب الوهمية"""
        return self.account_info
    
    def symbol_info(self, symbol):
        """معلومات الرمز"""
        class SymbolInfo:
            def __init__(self):
                self.point = 0.01
                self.digits = 2
                self.spread = 20
                self.trade_tick_size = 0.01
        return SymbolInfo()
    
    def symbol_info_tick(self, symbol):
        """الأسعار اللحظية الوهمية"""
        class Tick:
            def __init__(self):
                self.time = datetime.now()
                self.bid = 2000.0 + random.uniform(-5, 5)
                self.ask = self.bid + 0.5
                self.last = self.bid
                self.volume = 1000
        return Tick()
    
    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        """
        توليد بيانات وهمية للشموع
        """
        import time
        
        # توليد بيانات عشوائية واقعية
        np.random.seed(42)
        base_price = 2000.0 if 'XAU' in symbol else (100.0 if 'DX' in symbol else 24.0)
        
        rates = []
        current_time = int(time.time())
        
        for i in range(count):
            # توليد حركة عشوائية
            change = np.random.normal(0, 0.001)
            open_price = base_price * (1 + change)
            high_price = open_price * (1 + abs(np.random.normal(0, 0.002)))
            low_price = open_price * (1 - abs(np.random.normal(0, 0.002)))
            close_price = (high_price + low_price) / 2 + np.random.normal(0, 0.1)
            volume = int(np.random.uniform(1000, 10000))
            
            rates.append({
                'time': current_time - (count - i) * 3600,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'tick_volume': volume,
                'spread': 20,
                'real_volume': volume
            })
            
            base_price = close_price
        
        return rates
    
    def order_send(self, request):
        """محاكاة إرسال الأمر"""
        class Result:
            def __init__(self):
                self.retcode = 10009  # TRADE_RETCODE_DONE
                self.deal = 12345
                self.order = 67890
                self.volume = request.get('volume', 0.1)
                self.price = request.get('price', 2000.0)
        return Result()
    
    def positions_total(self):
        """عدد الصفقات المفتوحة"""
        return 0
    
    def positions_get(self):
        """الصفقات المفتوحة"""
        return []


# محاكاة الثوابت
TIMEFRAME_M1 = 1
TIMEFRAME_M5 = 5
TIMEFRAME_M15 = 15
TIMEFRAME_M30 = 30
TIMEFRAME_H1 = 16385
TIMEFRAME_H4 = 16388
TIMEFRAME_D1 = 16408
TIMEFRAME_W1 = 32769

ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
ORDER_TYPE_BUY_LIMIT = 2
ORDER_TYPE_SELL_LIMIT = 3
ORDER_TYPE_BUY_STOP = 4
ORDER_TYPE_SELL_STOP = 5

TRADE_ACTION_DEAL = 1


# إنشاء نسخة عالمية
_mt5_instance = MockMT5()

# دوال مطابقة لواجهة MT5 الحقيقية
def initialize(path=None):
    return _mt5_instance.initialize(path)

def shutdown():
    return _mt5_instance.shutdown()

def login(login, password, server):
    return _mt5_instance.login(login, password, server)

def account_info():
    return _mt5_instance.account_info()

def symbol_info(symbol):
    return _mt5_instance.symbol_info(symbol)

def symbol_info_tick(symbol):
    return _mt5_instance.symbol_info_tick(symbol)

def copy_rates_from_pos(symbol, timeframe, start, count):
    return _mt5_instance.copy_rates_from_pos(symbol, timeframe, start, count)

def order_send(request):
    return _mt5_instance.order_send(request)

def positions_total():
    return _mt5_instance.positions_total()

def positions_get():
    return _mt5_instance.positions_get()
