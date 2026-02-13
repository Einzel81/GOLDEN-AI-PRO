"""
TimescaleDB Connector
موصل TimescaleDB للبيانات الزمنية
"""

import pandas as pd
from sqlalchemy import create_engine, text
from typing import Optional
from config.settings import settings


class TimescaleDB:
    """
    واجهة TimescaleDB
    """
    
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self._init_tables()
        
    def _init_tables(self):
        """إنشاء الجداول"""
        with self.engine.connect() as conn:
            # جدول OHLCV
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume DOUBLE PRECISION,
                    PRIMARY KEY (time, symbol, timeframe)
                );
            """))
            
            # تحويل إلى hypertable
            conn.execute(text("""
                SELECT create_hypertable('ohlcv', 'time', 
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
            """))
            
            # فهارس
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe 
                ON ohlcv (symbol, timeframe, time DESC);
            """))
            
            conn.commit()
    
    def save_ohlcv(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """حفظ بيانات OHLCV"""
        if df.empty:
            return
        
        # إعداد البيانات
        data = df.copy()
        data['symbol'] = symbol
        data['timeframe'] = timeframe
        data.reset_index(inplace=True)
        
        # إعادة تسمية الأعمدة
        if 'time' not in data.columns and 'timestamp' in data.columns:
            data.rename(columns={'timestamp': 'time'}, inplace=True)
        
        # Upsert
        with self.engine.connect() as conn:
            for _, row in data.iterrows():
                conn.execute(text("""
                    INSERT INTO ohlcv (time, symbol, timeframe, open, high, low, close, volume)
                    VALUES (:time, :symbol, :timeframe, :open, :high, :low, :close, :volume)
                    ON CONFLICT (time, symbol, timeframe) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume;
                """), row.to_dict())
            
            conn.commit()
    
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """جلب بيانات OHLCV"""
        query = """
            SELECT time, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = :symbol AND timeframe = :timeframe
        """
        
        params = {'symbol': symbol, 'timeframe': timeframe}
        
        if start:
            query += " AND time >= :start"
            params['start'] = start
        
        if end:
            query += " AND time <= :end"
            params['end'] = end
        
        query += " ORDER BY time DESC LIMIT :limit"
        params['limit'] = limit
        
        df = pd.read_sql(text(query), self.engine, params=params)
        
        if not df.empty:
            df.set_index('time', inplace=True)
            df.sort_index(inplace=True)
        
        return df
