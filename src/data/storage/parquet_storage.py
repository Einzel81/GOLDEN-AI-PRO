"""
تخزين Parquet
Parquet Storage for efficient data storage
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from loguru import logger


class ParquetStorage:
    """
    تخزين فعال باستخدام Parquet
    """
    
    def __init__(self, base_path: str = "data/parquet"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _get_file_path(self, symbol: str, timeframe: str, date: datetime) -> Path:
        """الحصول على مسار الملف"""
        # تنظيم حسب: symbol/timeframe/year/month/data.parquet
        path = (
            self.base_path / 
            symbol / 
            timeframe / 
            str(date.year) / 
            f"{date.month:02d}" /
            f"{date.day:02d}.parquet"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    def save_ohlcv(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ):
        """حفظ بيانات OHLCV"""
        if df.empty:
            return
        
        # تجميع حسب اليوم
        df = df.copy()
        df['date'] = df.index.date
        
        for date, group in df.groupby('date'):
            file_path = self._get_file_path(symbol, timeframe, pd.Timestamp(date))
            
            # دمج مع البيانات الموجودة إن وجدت
            if file_path.exists():
                existing = pd.read_parquet(file_path)
                combined = pd.concat([existing, group.drop('date', axis=1)])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined = combined.sort_index()
            else:
                combined = group.drop('date', axis=1)
            
            # حفظ بضغط عالي
            table = pa.Table.from_pandas(combined)
            pq.write_table(
                table, 
                file_path,
                compression='zstd',
                use_dictionary=True
            )
        
        logger.info(f"Saved {len(df)} rows to Parquet for {symbol} {timeframe}")
    
    def load_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """تحميل بيانات OHLCV"""
        
        # تحديد نطاق التواريخ
        if start is None:
            start = datetime.now() - timedelta(days=30)
        if end is None:
            end = datetime.now()
        
        # جمع جميع الملفات في النطاق
        files = []
        current = start
        
        while current <= end:
            file_path = self._get_file_path(symbol, timeframe, current)
            if file_path.exists():
                files.append(file_path)
            current += timedelta(days=1)
        
        if not files:
            return pd.DataFrame()
        
        # قراءة ودمج
        dfs = [pd.read_parquet(f) for f in files]
        combined = pd.concat(dfs)
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        
        # فلترة النطاق الدقيق
        mask = (combined.index >= start) & (combined.index <= end)
        return combined.loc[mask]
    
    def get_available_symbols(self) -> List[str]:
        """الحصول على الرموز المتاحة"""
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]
    
    def get_date_range(self, symbol: str, timeframe: str) -> Dict:
        """الحصول على نطاق التواريخ المتاح"""
        path = self.base_path / symbol / timeframe
        
        if not path.exists():
            return {'min': None, 'max': None}
        
        dates = []
        for year_dir in path.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_file in month_dir.glob("*.parquet"):
                    dates.append(pd.Timestamp(f"{year_dir.name}-{month_dir.name}-{day_file.stem}"))
        
        if not dates:
            return {'min': None, 'max': None}
        
        return {
            'min': min(dates).isoformat(),
            'max': max(dates).isoformat(),
            'total_days': len(dates)
        }
    
    def compact_files(self, symbol: str, timeframe: str):
        """ضغط الملفات الصغيرة"""
        path = self.base_path / symbol / timeframe
        
        if not path.exists():
            return
        
        for year_dir in path.iterdir():
            if not year_dir.is_dir():
                continue
            
            # دمج جميع ملفات الشهر في ملف واحد
            for month_dir in year_dir.iterdir():
                files = list(month_dir.glob("*.parquet"))
                
                if len(files) > 1:
                    dfs = [pd.read_parquet(f) for f in files]
                    combined = pd.concat(dfs)
                    combined = combined[~combined.index.duplicated(keep='last')]
                    
                    # حفظ في ملف واحد
                    output_file = month_dir / "combined.parquet"
                    combined.to_parquet(output_file, compression='zstd')
                    
                    # حذف الملفات القديمة
                    for f in files:
                        f.unlink()
                    
                    logger.info(f"Compacted {len(files)} files in {month_dir}")
    
    def get_storage_stats(self) -> Dict:
        """إحصائيات التخزين"""
        total_size = 0
        file_count = 0
        
        for file in self.base_path.rglob("*.parquet"):
            total_size += file.stat().st_size
            file_count += 1
        
        return {
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'symbols': len(self.get_available_symbols())
        }
