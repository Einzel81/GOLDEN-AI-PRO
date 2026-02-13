"""
المصادقة والأمان
Authentication Middleware
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional

from config.settings import settings


security = HTTPBearer()


class AuthMiddleware:
    """
    وسيط المصادقة
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY or "your-secret-key-change-in-production"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        
    def create_access_token(self, data: dict) -> str:
        """إنشاء توكن"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """التحقق من التوكن"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    async def __call__(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> dict:
        """التحقق من الطلب"""
        token = credentials.credentials
        payload = self.verify_token(token)
        
        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload


# Dependency for protected routes
async def get_current_user(token: dict = Depends(AuthMiddleware())):
    """الحصول على المستخدم الحالي"""
    return token
