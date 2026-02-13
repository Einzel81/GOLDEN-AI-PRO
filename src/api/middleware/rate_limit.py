"""
تقييد المعدل
Rate Limiting Middleware
"""

import time
from typing import Dict, Optional
from fastapi import Request, HTTPException
from loguru import logger


class RateLimiter:
    """
    مقيد المعدل (Requests per minute)
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}  # IP -> timestamps
        
    async def check_rate_limit(self, request: Request):
        """التحقق من المعدل"""
        client_ip = request.client.host
        current_time = time.time()
        
        # تنظيف الطلبات القديمة
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if current_time - ts < 60
            ]
        else:
            self.requests[client_ip] = []
        
        # التحقق من الحد
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # إضافة الطلب الحالي
        self.requests[client_ip].append(current_time)
        
        return True
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """الحصول على العدد المتبقي"""
        if client_ip not in self.requests:
            return self.requests_per_minute
        
        current_time = time.time()
        recent_requests = [
            ts for ts in self.requests[client_ip]
            if current_time - ts < 60
        ]
        
        return max(0, self.requests_per_minute - len(recent_requests))


rate_limiter = RateLimiter()
