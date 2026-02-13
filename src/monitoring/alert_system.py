"""
نظام التنبيهات المتكامل
Multi-channel Alert System
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import aiohttp
from loguru import logger


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class Alert:
    """تنبيه"""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict] = None


class AlertManager:
    """
    مدير تنبيهات متعدد القنوات
    """
    
    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        discord_webhook: Optional[str] = None
    ):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.discord_webhook = discord_webhook
        
        self.enabled_channels: List[AlertChannel] = []
        self._setup_channels()
        
        self.alert_history: List[Alert] = []
        self.rate_limits: Dict[AlertChannel, datetime] = {}
        
    def _setup_channels(self):
        """إعداد القنوات المتاحة"""
        if self.telegram_token and self.telegram_chat_id:
            self.enabled_channels.append(AlertChannel.TELEGRAM)
        
        if self.discord_webhook:
            self.enabled_channels.append(AlertChannel.DISCORD)
    
    async def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        metadata: Optional[Dict] = None,
        channels: Optional[List[AlertChannel]] = None
    ):
        """إرسال تنبيه"""
        alert = Alert(
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self.alert_history.append(alert)
        
        target_channels = channels or self.enabled_channels
        
        tasks = []
        for channel in target_channels:
            if channel == AlertChannel.TELEGRAM:
                tasks.append(self._send_telegram(alert))
            elif channel == AlertChannel.DISCORD:
                tasks.append(self._send_discord(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # تسجيل محلي
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(level, logger.info)
        
        log_method(f"[{level.value.upper()}] {title}: {message}")
    
    async def _send_telegram(self, alert: Alert):
        """إرسال عبر Telegram"""
        if not self.telegram_token:
            return
        
        emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }.get(alert.level, "ℹ️")
        
        text = f"{emoji} <b>{alert.title}</b>\n\n"
        text += f"{alert.message}\n\n"
        text += f"⏰ {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        if alert.metadata:
            text += f"\n\n📊 Metadata:\n<pre>{str(alert.metadata)}</pre>"
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Telegram alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Telegram alert error: {e}")
    
    async def _send_discord(self, alert: Alert):
        """إرسال عبر Discord"""
        if not self.discord_webhook:
            return
        
        color = {
            AlertLevel.INFO: 0x3498db,
            AlertLevel.WARNING: 0xf1c40f,
            AlertLevel.ERROR: 0xe74c3c,
            AlertLevel.CRITICAL: 0x992d22
        }.get(alert.level, 0x3498db)
        
        embed = {
            'title': alert.title,
            'description': alert.message,
            'color': color,
            'timestamp': alert.timestamp.isoformat(),
            'footer': {'text': f'Golden-AI Pro | {alert.level.value.upper()}'}
        }
        
        if alert.metadata:
            fields = []
            for key, value in alert.metadata.items():
                fields.append({
                    'name': key,
                    'value': str(value)[:1024],
                    'inline': True
                })
            embed['fields'] = fields
        
        payload = {'embeds': [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.discord_webhook,
                    json=payload,
                    timeout=10
                ) as response:
                    if response.status not in [200, 204]:
                        logger.error(f"Failed to send Discord alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Discord alert error: {e}")
    
    async def send_trade_alert(
        self,
        action: str,
        symbol: str,
        entry: float,
        sl: float,
        tp: float,
        lots: float,
        confidence: float
    ):
        """تنبيه خاص بالصفقة"""
        emoji = "🟢" if action == "buy" else "🔴"
        
        title = f"{emoji} New Trade Executed"
        message = (
            f"Symbol: {symbol}\n"
            f"Action: {action.upper()}\n"
            f"Entry: {entry}\n"
            f"SL: {sl}\n"
            f"TP: {tp}\n"
            f"Lots: {lots}\n"
            f"Confidence: {confidence:.1%}"
        )
        
        await self.send_alert(
            level=AlertLevel.INFO,
            title=title,
            message=message
        )
    
    async def send_error_alert(self, error_message: str, context: Optional[Dict] = None):
        """تنبيه خطأ"""
        await self.send_alert(
            level=AlertLevel.ERROR,
            title="System Error",
            message=error_message,
            metadata=context
        )
    
    def get_alert_history(
        self,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Alert]:
        """الحصول على سجل التنبيهات"""
        alerts = self.alert_history
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts[-limit:]
