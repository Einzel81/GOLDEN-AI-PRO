"""
Redis Cache
التخزين المؤقت باستخدام Redis
"""

import pickle
import json
from typing import Optional, Any, Union
import redis
from config.settings import settings


class RedisCache:
    """
    واجهة Redis للتخزين المؤقت
    """
    
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL)
        
    def get(self, key: str) -> Optional[Any]:
        """جلب قيمة"""
        data = self.client.get(key)
        
        if data is None:
            return None
        
        try:
            return pickle.loads(data)
        except:
            try:
                return json.loads(data)
            except:
                return data.decode('utf-8')
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300  # 5 دقائق افتراضياً
    ):
        """حفظ قيمة"""
        try:
            serialized = pickle.dumps(value)
        except:
            serialized = json.dumps(value).encode('utf-8')
        
        self.client.setex(key, ttl, serialized)
    
    def delete(self, key: str):
        """حذف مفتاح"""
        self.client.delete(key)
    
    def exists(self, key: str) -> bool:
        """التحقق من وجود المفتاح"""
        return self.client.exists(key) > 0
    
    def clear_pattern(self, pattern: str):
        """مسح جميع المفاتيح المطابقة للنمط"""
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)
    
    def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: int = 300
    ) -> Any:
        """جلب أو إنشاء"""
        value = self.get(key)
        
        if value is None:
            value = factory()
            self.set(key, value, ttl)
        
        return value
