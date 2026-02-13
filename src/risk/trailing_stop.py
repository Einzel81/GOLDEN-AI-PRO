"""
وقف الخسارة المتحرك الذكي
Smart Trailing Stop with multiple strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass


class TrailingStrategy(Enum):
    FIXED_DISTANCE = "fixed_distance"
    ATR_BASED = "atr_based"
    PARABOLIC_SAR = "parabolic_sar"
    MOVING_AVERAGE = "moving_average"
    CHANDELIER_EXIT = "chandelier_exit"


@dataclass
class TrailingStopConfig:
    """إعدادات Trailing Stop"""
    strategy: TrailingStrategy
    activation_pips: float
    distance_pips: float
    atr_multiplier: float = 2.0
    ma_period: int = 20


class TrailingStopManager:
    """
    مدير Trailing Stop متعدد الاستراتيجيات
    """
    
    def __init__(self):
        self.active_stops: Dict[int, Dict] = {}  # ticket -> config
        self.price_history: Dict[int, list] = {}  # ticket -> prices
        
    def add_trailing_stop(
        self,
        ticket: int,
        entry_price: float,
        current_price: float,
        position_type: str,  # 'buy' or 'sell'
        config: TrailingStopConfig
    ):
        """إضافة trailing stop لمركز"""
        self.active_stops[ticket] = {
            'entry': entry_price,
            'highest_price': current_price if position_type == 'buy' else entry_price,
            'lowest_price': current_price if position_type == 'sell' else entry_price,
            'current_stop': None,
            'activated': False,
            'config': config,
            'type': position_type
        }
        self.price_history[ticket] = []
        
    def update(self, ticket: int, current_price: float, atr: Optional[float] = None) -> Optional[float]:
        """
        تحديث Trailing Stop وإرجاع السعر الجديد إذا تغير
        """
        if ticket not in self.active_stops:
            return None
        
        stop_data = self.active_stops[ticket]
        config = stop_data['config']
        
        # تسجيل السعر
        self.price_history[ticket].append(current_price)
        
        # التحقق من التفعيل
        if not stop_data['activated']:
            profit_pips = self._calculate_profit_pips(
                stop_data['entry'], current_price, stop_data['type']
            )
            
            if profit_pips >= config.activation_pips:
                stop_data['activated'] = True
                # تعيين SL أولي عند التفعيل
                initial_stop = self._calculate_initial_stop(
                    stop_data['entry'], current_price, stop_data['type'], config
                )
                stop_data['current_stop'] = initial_stop
                return initial_stop
            return None
        
        # حساب SL الجديد
        new_stop = self._calculate_trailing_stop(
            current_price, stop_data, config, atr
        )
        
        # التحقق من التحسن
        if self._is_better_stop(new_stop, stop_data['current_stop'], stop_data['type']):
            stop_data['current_stop'] = new_stop
            return new_stop
        
        return None
    
    def _calculate_profit_pips(self, entry: float, current: float, pos_type: str) -> float:
        """حساب الربح بالنقاط"""
        if pos_type == 'buy':
            return (current - entry) / 0.01  # XAUUSD
        else:
            return (entry - current) / 0.01
    
    def _calculate_initial_stop(
        self,
        entry: float,
        current: float,
        pos_type: str,
        config: TrailingStopConfig
    ) -> float:
        """حساب SL أولي عند التفعيل"""
        if pos_type == 'buy':
            return current - (config.distance_pips * 0.01)
        else:
            return current + (config.distance_pips * 0.01)
    
    def _calculate_trailing_stop(
        self,
        current_price: float,
        stop_data: Dict,
        config: TrailingStopConfig,
        atr: Optional[float]
    ) -> float:
        """حساب Trailing Stop حسب الاستراتيجية"""
        strategy = config.strategy
        pos_type = stop_data['type']
        
        if strategy == TrailingStrategy.FIXED_DISTANCE:
            return self._fixed_distance_stop(current_price, config.distance_pips, pos_type)
        
        elif strategy == TrailingStrategy.ATR_BASED and atr:
            return self._atr_based_stop(current_price, atr, config.atr_multiplier, pos_type)
        
        elif strategy == TrailingStrategy.MOVING_AVERAGE:
            return self._ma_based_stop(current_price, stop_data, config.ma_period, pos_type)
        
        elif strategy == TrailingStrategy.CHANDELIER_EXIT:
            return self._chandelier_stop(current_price, stop_data, config, atr, pos_type)
        
        return stop_data['current_stop']
    
    def _fixed_distance_stop(self, price: float, distance_pips: float, pos_type: str) -> float:
        """Fixed Distance Trailing Stop"""
        distance = distance_pips * 0.01
        if pos_type == 'buy':
            return price - distance
        return price + distance
    
    def _atr_based_stop(
        self,
        price: float,
        atr: float,
        multiplier: float,
        pos_type: str
    ) -> float:
        """ATR-Based Trailing Stop"""
        distance = atr * multiplier
        if pos_type == 'buy':
            return price - distance
        return price + distance
    
    def _ma_based_stop(
        self,
        price: float,
        stop_data: Dict,
        period: int,
        pos_type: str
    ) -> float:
        """Moving Average Trailing Stop"""
        prices = self.price_history[stop_data.get('ticket', 0)]
        if len(prices) < period:
            return stop_data['current_stop']
        
        ma = np.mean(prices[-period:])
        
        if pos_type == 'buy':
            return min(ma, price - 0.5)  # buffer
        return max(ma, price + 0.5)
    
    def _chandelier_stop(
        self,
        price: float,
        stop_data: Dict,
        config: TrailingStopConfig,
        atr: Optional[float],
        pos_type: str
    ) -> float:
        """Chandelier Exit Trailing Stop"""
        prices = self.price_history.get(stop_data.get('ticket', 0), [])
        if len(prices) < 22 or atr is None:
            return stop_data['current_stop']
        
        period = 22
        atr_mult = config.atr_multiplier
        
        if pos_type == 'buy':
            highest_high = max(prices[-period:])
            return highest_high - (atr * atr_mult)
        else:
            lowest_low = min(prices[-period:])
            return lowest_low + (atr * atr_mult)
    
    def _is_better_stop(self, new_stop: float, current_stop: float, pos_type: str) -> bool:
        """التحقق إذا كان الـ SL الجديد أفضل"""
        if current_stop is None:
            return True
        
        if pos_type == 'buy':
            return new_stop > current_stop
        return new_stop < current_stop
    
    def remove_trailing_stop(self, ticket: int):
        """إزالة trailing stop"""
        if ticket in self.active_stops:
            del self.active_stops[ticket]
        if ticket in self.price_history:
            del self.price_history[ticket]
    
    def get_status(self, ticket: int) -> Optional[Dict]:
        """الحصول على حالة Trailing Stop"""
        if ticket not in self.active_stops:
            return None
        
        data = self.active_stops[ticket]
        return {
            'activated': data['activated'],
            'current_stop': data['current_stop'],
            'entry': data['entry'],
            'profit_pips': self._calculate_profit_pips(
                data['entry'], 
                data['highest_price'] if data['type'] == 'buy' else data['lowest_price'],
                data['type']
            ) if data['activated'] else 0
        }
