"""
إعدادات التسجيل
Logging Configuration
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Dict, Any


class LoggingConfig:
    """
    إعدادات التسجيل المتقدمة
    """
    
    @staticmethod
    def setup(
        log_level: str = "INFO",
        log_dir: str = "logs",
        max_file_size: str = "10 MB",
        retention: str = "30 days"
    ):
        """إعداد التسجيل"""
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # إزالة المعالج الافتراضي
        logger.remove()
        
        # تسجيل في الكونسول
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            colorize=True
        )
        
        # تسجيل في ملف عام
        logger.add(
            log_path / "app.log",
            rotation=max_file_size,
            retention=retention,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            compression="zip"
        )
        
        # تسجيل الأخطاء في ملف منفصل
        logger.add(
            log_path / "errors.log",
            rotation=max_file_size,
            retention=retention,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
            backtrace=True,
            diagnose=True
        )
        
        # تسجيل الصفقات في ملف منفصل
        logger.add(
            log_path / "trades.log",
            rotation="5 MB",
            retention="60 days",
            level="INFO",
            filter=lambda record: "trade" in record["extra"],
            format="{time:YYYY-MM-DD HH:mm:ss} | {extra[trade]} | {message}"
        )
        
        logger.info("Logging configured successfully")
    
    @staticmethod
    def get_logger(name: str):
        """الحصول على مسجل مخصص"""
        return logger.bind(context=name)


# إعداد افتراضي
LoggingConfig.setup()
