"""
WebSocket Routes
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json

from src.data.connectors.mt5_connector import mt5_connector
from config.settings import settings

router = APIRouter()


class ConnectionManager:
    """
    إدارة اتصالات WebSocket
    """
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket للبيانات اللحظية
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # إرسال تحديثات الأسعار
            if mt5_connector.connected:
                try:
                    tick = await mt5_connector.get_tick(settings.SYMBOL)
                    await websocket.send_json({
                        "type": "tick",
                        "data": tick
                    })
                except:
                    pass
            
            # الاستماع للرسائل من العميل
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                message = json.loads(data)
                
                # معالجة الأوامر
                if message.get("action") == "subscribe":
                    # إضافة إلى قناة محددة
                    pass
                    
            except asyncio.TimeoutError:
                pass
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
