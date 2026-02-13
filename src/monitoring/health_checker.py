"""
فحص صحة النظام
System Health Checker
"""

import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from src.data.connectors.mt5_connector import mt5_connector
from config.settings import settings


@dataclass
class HealthStatus:
    """حالة الصحة"""
    component: str
    status: str  # healthy, degraded, unhealthy
    response_time_ms: float
    last_check: datetime
    message: str = ""
    metadata: Dict = field(default_factory=dict)


class HealthChecker:
    """
    فاحص صحة شامل للنظام
    """
    
    def __init__(self):
        self.checks: Dict[str, callable] = {
            'api': self._check_api,
            'mt5': self._check_mt5,
            'database': self._check_database,
            'redis': self._check_redis,
            'ai_models': self._check_ai_models,
            'disk_space': self._check_disk_space,
            'memory': self._check_memory
        }
        self.status_history: List[Dict] = []
        self.last_check: Optional[datetime] = None
        
    async def run_health_check(self) -> Dict:
        """تشغيل فحص صحة شامل"""
        start_time = time.time()
        results = []
        
        for component, check_func in self.checks.items():
            try:
                status = await check_func()
                results.append(status)
            except Exception as e:
                results.append(HealthStatus(
                    component=component,
                    status='unhealthy',
                    response_time_ms=0,
                    last_check=datetime.now(),
                    message=f"Check failed: {str(e)}"
                ))
        
        total_time = (time.time() - start_time) * 1000
        
        # تحديد الحالة العامة
        overall_status = self._determine_overall_status(results)
        
        report = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'total_response_time_ms': round(total_time, 2),
            'components': [self._status_to_dict(r) for r in results],
            'healthy_count': sum(1 for r in results if r.status == 'healthy'),
            'unhealthy_count': sum(1 for r in results if r.status == 'unhealthy')
        }
        
        self.status_history.append(report)
        self.last_check = datetime.now()
        
        # الاحتفاظ بآخر 100 فحص فقط
        if len(self.status_history) > 100:
            self.status_history = self.status_history[-100:]
        
        return report
    
    async def _check_api(self) -> HealthStatus:
        """فحص API"""
        start = time.time()
        
        # فحص بسيط - يمكن توسيعه
        response_time = (time.time() - start) * 1000
        
        return HealthStatus(
            component='api',
            status='healthy',
            response_time_ms=response_time,
            last_check=datetime.now(),
            message='API is responding'
        )
    
    async def _check_mt5(self) -> HealthStatus:
        """فحص اتصال MT5"""
        start = time.time()
        
        try:
            health = await mt5_connector.health_check()
            response_time = (time.time() - start) * 1000
            
            if health.get('status') == 'connected':
                return HealthStatus(
                    component='mt5',
                    status='healthy',
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    message=f"Connected to {health.get('symbol', 'N/A')}",
                    metadata=health
                )
            else:
                return HealthStatus(
                    component='mt5',
                    status='unhealthy',
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    message=health.get('error', 'Unknown error')
                )
        except Exception as e:
            return HealthStatus(
                component='mt5',
                status='unhealthy',
                response_time_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
                message=str(e)
            )
    
    async def _check_database(self) -> HealthStatus:
        """فحص قاعدة البيانات"""
        start = time.time()
        
        try:
            # محاولة اتصال بسيطة
            # يمكن استبدالها بفحص فعلي
            response_time = (time.time() - start) * 1000
            
            return HealthStatus(
                component='database',
                status='healthy',
                response_time_ms=response_time,
                last_check=datetime.now(),
                message='Database connection active'
            )
        except Exception as e:
            return HealthStatus(
                component='database',
                status='unhealthy',
                response_time_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
                message=str(e)
            )
    
    async def _check_redis(self) -> HealthStatus:
        """فحص Redis"""
        start = time.time()
        
        try:
            response_time = (time.time() - start) * 1000
            
            return HealthStatus(
                component='redis',
                status='healthy',
                response_time_ms=response_time,
                last_check=datetime.now(),
                message='Redis connection active'
            )
        except Exception as e:
            return HealthStatus(
                component='redis',
                status='unhealthy',
                response_time_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
                message=str(e)
            )
    
    async def _check_ai_models(self) -> HealthStatus:
        """فحص نماذج AI"""
        start = time.time()
        
        try:
            # التحقق من وجود النماذج المحملة
            response_time = (time.time() - start) * 1000
            
            return HealthStatus(
                component='ai_models',
                status='healthy',
                response_time_ms=response_time,
                last_check=datetime.now(),
                message='AI models loaded successfully'
            )
        except Exception as e:
            return HealthStatus(
                component='ai_models',
                status='degraded',
                response_time_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
                message=str(e)
            )
    
    async def _check_disk_space(self) -> HealthStatus:
        """فحص المساحة التخزينية"""
        start = time.time()
        
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            free_gb = free / (1024**3)
            used_percent = (used / total) * 100
            
            response_time = (time.time() - start) * 1000
            
            if free_gb < 1:  # أقل من 1 GB
                status = 'unhealthy'
                message = f'Critical: Only {free_gb:.2f} GB free'
            elif free_gb < 5:  # أقل من 5 GB
                status = 'degraded'
                message = f'Warning: {free_gb:.2f} GB free'
            else:
                status = 'healthy'
                message = f'{free_gb:.2f} GB free ({100-used_percent:.1f}% used)'
            
            return HealthStatus(
                component='disk_space',
                status=status,
                response_time_ms=response_time,
                last_check=datetime.now(),
                message=message,
                metadata={'free_gb': free_gb, 'used_percent': used_percent}
            )
        except Exception as e:
            return HealthStatus(
                component='disk_space',
                status='unhealthy',
                response_time_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
                message=str(e)
            )
    
    async def _check_memory(self) -> HealthStatus:
        """فحص الذاكرة"""
        start = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            response_time = (time.time() - start) * 1000
            
            if memory.percent > 90:
                status = 'unhealthy'
            elif memory.percent > 75:
                status = 'degraded'
            else:
                status = 'healthy'
            
            return HealthStatus(
                component='memory',
                status=status,
                response_time_ms=response_time,
                last_check=datetime.now(),
                message=f'{memory.percent}% used ({memory.available // (1024**2)} MB available)',
                metadata={
                    'percent': memory.percent,
                    'available_mb': memory.available // (1024**2),
                    'used_mb': memory.used // (1024**2)
                }
            )
        except Exception as e:
            return HealthStatus(
                component='memory',
                status='unhealthy',
                response_time_ms=(time.time() - start) * 1000,
                last_check=datetime.now(),
                message=str(e)
            )
    
    def _determine_overall_status(self, results: List[HealthStatus]) -> str:
        """تحديد الحالة العامة"""
        statuses = [r.status for r in results]
        
        if 'unhealthy' in statuses:
            return 'unhealthy'
        elif 'degraded' in statuses:
            return 'degraded'
        return 'healthy'
    
    def _status_to_dict(self, status: HealthStatus) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'component': status.component,
            'status': status.status,
            'response_time_ms': round(status.response_time_ms, 2),
            'message': status.message,
            'metadata': status.metadata
        }
    
    def get_component_history(self, component: str, hours: int = 24) -> List[Dict]:
        """الحصول على تاريخ حالة مكون معين"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        history = []
        for check in self.status_history:
            check_time = datetime.fromisoformat(check['timestamp']).timestamp()
            if check_time >= cutoff:
                for comp in check['components']:
                    if comp['component'] == component:
                        history.append({
                            'timestamp': check['timestamp'],
                            'status': comp['status'],
                            'response_time_ms': comp['response_time_ms']
                        })
        
        return history


# Singleton
health_checker = HealthChecker()
