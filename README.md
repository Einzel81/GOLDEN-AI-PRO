# 🏆 Golden-AI Pro

نظام تداول ذهب متكامل متقدم يجمع بين Smart Money Concepts (SMC) والذكاء الاصطناعي العميق.

## ✨ المميزات الرئيسية

### تحليل السوق
- **Smart Money Concepts (SMC)**: Order Blocks, Fair Value Gaps, Liquidity Sweeps, Market Structure
- **Volume Profile**: POC, Value Area, Volume Nodes
- **Price Action**: أنماط الشموع، الدعم والمقاومة
- **Kill Zones**: تحديد أوقات التداول الأمثل (London/NY/Asian)

### الذكاء الاصطناعي
- **LSTM + Attention**: نموذج متقدم للتنبؤ بالسلاسل الزمنية
- **Transformer Architecture**: للتنبؤات طويلة المدى
- **Ensemble Models**: دمج XGBoost, LightGBM
- **Fusion Engine**: دمج إشارات متعددة مع Confidence Scoring

### إدارة المخاطر
- **Dynamic Position Sizing**: حساب حجم المركز بناءً على المخاطر
- **Drawdown Protection**: حماية تلقائية من الخسارة المتتالية
- **Kelly Criterion**: تحسين حجم المركز رياضياً
- **Trailing Stop**: وقف خسارة متحرك ذكي

### الاتصال بـ MetaTrader 5
- **MT5 Connector**: اتصال مباشر عبر Python API
- **ZeroMQ Server**: EA متقدم لاستقبال الأوامر
- **Real-time Data**: بيانات لحظية مع WebSocket
- **Order Management**: إدارة أوامر متكاملة

## 🚀 التثبيت والتشغيل

### المتطلبات
- Python 3.10+
- MetaTrader 5
- Docker & Docker Compose (اختياري)

### التثبيت

```bash
# 1. Clone repository
git clone https://github.com/yourusername/golden-ai-pro.git
cd golden-ai-pro

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.example .env
# Edit .env with your settings

# 5. Run with Docker Compose (Recommended)
docker-compose up -d

# Or run locally
python -m src.api.main
