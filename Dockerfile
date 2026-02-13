FROM python:3.10-slim

WORKDIR /app

# تثبيت الأدوات الأساسية فقط
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# نسخ المتطلبات
COPY requirements.txt .

# تثبيت المكتبات (بدون TensorFlow)
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# إنشاء المجلدات
RUN mkdir -p logs models data config

# المنفذ
EXPOSE 5000

# الصحة
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# التشغيل
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "5000"]
