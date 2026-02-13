"""
مناطق الكيل (Kill Zones) - أوقات التداول الأمثل
Trading sessions with high probability setups
"""

import pandas as pd
from datetime import time, datetime
from typing import Dict, List, Tuple
import pytz

from config.settings import settings


class KillZoneDetector:
    """
    محدد مناطق الكيل:
    - London Kill Zone (07:00 - 10:00 UTC)
    - New York Kill Zone (12:00 - 15:00 UTC)
    - Asian Kill Zone (19:00 - 22:00 UTC)
    """
    
    def __init__(self):
        self.timezone = pytz.UTC
        
        # London Kill Zone
        self.london_start = self._parse_time(settings.LONDON_KILL_ZONE_START)
        self.london_end = self._parse_time(settings.LONDON_KILL_ZONE_END)
        
        # New York Kill Zone
        self.ny_start = self._parse_time(settings.NY_KILL_ZONE_START)
        self.ny_end = self._parse_time(settings.NY_KILL_ZONE_END)
        
        # Asian Kill Zone
        self.asian_start = self._parse_time(settings.ASIAN_KILL_ZONE_START)
        self.asian_end = self._parse_time(settings.ASIAN_KILL_ZONE_END)
        
    def _parse_time(self, time_str: str) -> time:
        """تحويل نص الوقت إلى كائن time"""
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    
    def is_in_kill_zone(self, timestamp: pd.Timestamp) -> bool:
        """
        التحقق مما إذا كان الوقت الحالي في منطقة كيل
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize('UTC')
        else:
            timestamp = timestamp.tz_convert('UTC')
        
        current_time = timestamp.time()
        
        # London
        if self.london_start <= current_time <= self.london_end:
            return True
        
        # New York
        if self.ny_start <= current_time <= self.ny_end:
            return True
        
        # Asian (تداول أقل أهمية للذهب)
        # if self.asian_start <= current_time <= self.asian_end:
        #     return True
        
        return False
    
    def get_current_session(self, timestamp: pd.Timestamp) -> str:
        """
        تحديد الجلسة الحالية
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize('UTC')
        else:
            timestamp = timestamp.tz_convert('UTC')
        
        current_time = timestamp.time()
        
        if self.london_start <= current_time <= self.london_end:
            return "London"
        elif self.ny_start <= current_time <= self.ny_end:
            return "New York"
        elif self.asian_start <= current_time <= self.asian_end:
            return "Asian"
        else:
            return "Off-Session"
    
    def get_session_high_probability(self, timestamp: pd.Timestamp) -> float:
        """
        حساب احتمالية النجاح بناءً على الجلسة
        """
        session = self.get_current_session(timestamp)
        
        probabilities = {
            "London": 0.75,
            "New York": 0.80,
            "Asian": 0.60,
            "Off-Session": 0.40
        }
        
        return probabilities.get(session, 0.40)
    
    def get_next_kill_zone(self, timestamp: pd.Timestamp) -> Dict:
        """
        الحصول على تفاصيل منطقة الكيل القادمة
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize('UTC')
        
        current_time = timestamp.time()
        
        # تحديد المنطقة القادمة
        sessions = [
            ("London", self.london_start, self.london_end),
            ("New York", self.ny_start, self.ny_end),
        ]
        
        for session_name, start, end in sessions:
            if current_time < start:
                return {
                    'name': session_name,
                    'start': start,
                    'end': end,
                    'minutes_until': self._minutes_until(current_time, start)
                }
        
        # إذا تجاوزنا جميع الجلسات، فالجلسة القادمة هي London غداً
        return {
            'name': 'London (Tomorrow)',
            'start': self.london_start,
            'end': self.london_end,
            'minutes_until': self._minutes_until(current_time, self.london_start) + 24*60
        }
    
    def _minutes_until(self, current: time, target: time) -> int:
        """حساب الدقائق المتبقية حتى وقت محدد"""
        current_minutes = current.hour * 60 + current.minute
        target_minutes = target.hour * 60 + target.minute
        
        if target_minutes > current_minutes:
            return target_minutes - current_minutes
        else:
            return (24 * 60) - current_minutes + target_minutes
