"""
مسجل الصفقات المتقدم
Advanced Trade Logger with structured logging
"""

import json
import gzip
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from loguru import logger
import pandas as pd


@dataclass
class TradeLogEntry:
    """مدخل سجل الصفقة"""
    timestamp: str
    level: str
    event_type: str  # ENTRY, EXIT, MODIFY, ERROR
    trade_id: str
    symbol: str
    action: str
    price: float
    volume: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    metadata: Optional[Dict] = None


class TradeLogger:
    """
    مسجل صفقات منظم مع:
    - تسجيل منظم (JSON)
    - ضغط تلقائي للملفات القديمة
    - البحث والتصفية
    """
    
    def __init__(self, log_dir: str = "logs/trades"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.current_file = self.log_dir / f"trades_{self.current_date}.jsonl"
        
        # إعداد Loguru
        logger.add(
            self.log_dir / "trade_errors.log",
            rotation="10 MB",
            retention="30 days",
            level="ERROR",
            filter=lambda record: record["extra"].get("trade") == True
        )
    
    def log_trade(self, entry: TradeLogEntry):
        """تسجيل صفقة"""
        # التحقق من تغيير التاريخ
        new_date = datetime.now().strftime('%Y-%m-%d')
        if new_date != self.current_date:
            self._rotate_file()
            self.current_date = new_date
            self.current_file = self.log_dir / f"trades_{self.current_date}.jsonl"
        
        # كتابة إلى الملف
        with open(self.current_file, 'a') as f:
            json.dump(asdict(entry), f)
            f.write('\n')
        
        # تسجيل في Loguru
        trade_logger = logger.bind(trade=True)
        
        if entry.event_type == "ENTRY":
            trade_logger.info(
                f"TRADE ENTRY: {entry.action} {entry.symbol} @ {entry.price} "
                f"Vol: {entry.volume} SL: {entry.stop_loss} TP: {entry.take_profit}"
            )
        elif entry.event_type == "EXIT":
            trade_logger.info(
                f"TRADE EXIT: {entry.trade_id} PnL: {entry.pnl}"
            )
        elif entry.event_type == "ERROR":
            trade_logger.error(f"TRADE ERROR: {entry.trade_id} - {entry.metadata}")
    
    def log_entry(
        self,
        trade_id: str,
        symbol: str,
        action: str,
        price: float,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict] = None
    ):
        """تسجيل دخول صفقة"""
        entry = TradeLogEntry(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            event_type="ENTRY",
            trade_id=trade_id,
            symbol=symbol,
            action=action,
            price=price,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata
        )
        self.log_trade(entry)
    
    def log_exit(
        self,
        trade_id: str,
        symbol: str,
        exit_price: float,
        pnl: float,
        metadata: Optional[Dict] = None
    ):
        """تسجيل خروج من صفقة"""
        entry = TradeLogEntry(
            timestamp=datetime.now().isoformat(),
            level="INFO",
            event_type="EXIT",
            trade_id=trade_id,
            symbol=symbol,
            action="CLOSE",
            price=exit_price,
            volume=0,
            pnl=pnl,
            metadata=metadata
        )
        self.log_trade(entry)
    
    def log_error(self, trade_id: str, error_message: str, metadata: Optional[Dict] = None):
        """تسجيل خطأ"""
        entry = TradeLogEntry(
            timestamp=datetime.now().isoformat(),
            level="ERROR",
            event_type="ERROR",
            trade_id=trade_id,
            symbol="",
            action="ERROR",
            price=0,
            volume=0,
            metadata={'error': error_message, **(metadata or {})}
        )
        self.log_trade(entry)
    
    def get_trades(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[TradeLogEntry]:
        """الحصول على صفقات"""
        trades = []
        
        # تحديد الملفات
        files = list(self.log_dir.glob("trades_*.jsonl*"))
        
        for file in files:
            # التحقق من التاريخ إذا كان في الاسم
            if start_date or end_date:
                file_date = file.stem.split('_')[1]
                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue
            
            # قراءة الملف (مع التعامل مع الضغط)
            opener = gzip.open if file.suffix == '.gz' else open
            
            try:
                with opener(file, 'rt') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        
                        # تصفية
                        if symbol and data.get('symbol') != symbol:
                            continue
                        if event_type and data.get('event_type') != event_type:
                            continue
                        
                        trades.append(TradeLogEntry(**data))
            except Exception as e:
                logger.error(f"Error reading {file}: {e}")
        
        return sorted(trades, key=lambda x: x.timestamp)
    
    def get_trade_stats(self, days: int = 7) -> Dict:
        """إحصائيات الصفقات"""
        cutoff = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
        
        trades = self.get_trades(start_date=cutoff)
        
        entries = [t for t in trades if t.event_type == 'ENTRY']
        exits = [t for t in trades if t.event_type == 'EXIT']
        errors = [t for t in trades if t.event_type == 'ERROR']
        
        total_pnl = sum(e.pnl for e in exits if e.pnl)
        
        return {
            'period_days': days,
            'total_entries': len(entries),
            'total_exits': len(exits),
            'total_errors': len(errors),
            'total_pnl': round(total_pnl, 2),
            'symbols_traded': len(set(e.symbol for e in entries)),
            'avg_pnl_per_trade': round(total_pnl / len(exits), 2) if exits else 0
        }
    
    def _rotate_file(self):
        """تدوير الملف (ضغط الملف القديم)"""
        if self.current_file.exists():
            compressed = self.current_file.with_suffix('.jsonl.gz')
            with open(self.current_file, 'rb') as f_in:
                with gzip.open(compressed, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            self.current_file.unlink()
            logger.info(f"Rotated and compressed {self.current_file.name}")
    
    def cleanup_old_files(self, days_to_keep: int = 90):
        """تنظيف الملفات القديمة"""
        cutoff = (datetime.now() - pd.Timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
        
        for file in self.log_dir.glob("trades_*.jsonl*"):
            file_date = file.stem.split('_')[1]
            if file_date < cutoff:
                file.unlink()
                logger.info(f"Deleted old log file: {file.name}")


# Singleton
trade_logger = TradeLogger()
