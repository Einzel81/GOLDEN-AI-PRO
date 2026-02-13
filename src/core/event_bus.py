"""
ناقل الأحداث
Event Bus for decoupled communication
"""

from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
from loguru import logger


@dataclass
class Event:
    """حدث"""
    type: str
    data: Any
    timestamp: datetime
    source: str


class EventBus:
    """
    ناقل أحداث غير متزامن
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
    def subscribe(self, event_type: str, handler: Callable):
        """الاشتراك في نوع حدث"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type}")
        
    def unsubscribe(self, event_type: str, handler: Callable):
        """إلغاء الاشتراك"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(handler)
    
    async def publish(self, event_type: str, data: Any, source: str = "system"):
        """نشر حدث"""
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=source
        )
        
        await self.event_queue.put(event)
        logger.debug(f"Event published: {event_type}")
    
    async def start(self):
        """بدء معالجة الأحداث"""
        self.running = True
        
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # معالجة الحدث
                handlers = self.subscribers.get(event.type, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(event))
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error(f"Event handler error: {e}")
                        
            except asyncio.TimeoutError:
                continue
    
    def stop(self):
        """إيقاف المعالجة"""
        self.running = False


# Singleton
event_bus = EventBus()
