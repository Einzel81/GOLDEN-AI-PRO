"""
نقطة الدخول الرئيسية لـ Golden AI Pro
API كامل مع دمج DXY والمعادن
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# إضافة المسار الرئيسي
sys.path.append(str(Path(__file__).parent.parent))

# الاستيرادات الداخلية
from data.multi_asset_collector import MultiAssetDataCollector, fetch_market_context
from analysis.correlation_engine import CorrelationAnalyzer, CorrelationSignal
from analysis.smc_analyzer import SMCAnalyzer  # افتراضي
from strategies.correlation_strategy import DXYCorrelationStrategy, TradingDecision
from ml.features import FeatureEngineer, extract_features
from ml.predictor import GoldPredictor  # افتراضي
from risk.manager import RiskManager  # افتراضي
from mt5.connector import MT5Connector  # افتراضي

# إعداد اللوجن
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# تحميل الإعدادات
load_dotenv()

# إنشاء التطبيق
app = Flask(__name__)
CORS(app)


class GoldenAIPro:
    """
    النظام الرئيسي المتكامل
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.data_collector: Optional[MultiAssetDataCollector] = None
        self.correlation_analyzer = CorrelationAnalyzer(self.config)
        self.correlation_strategy = DXYCorrelationStrategy(self.config)
        self.feature_engineer = FeatureEngineer(self.config)
        self.smc_analyzer = SMCAnalyzer() if hasattr(SMCAnalyzer, '__init__') else None
        self.predictor = GoldPredictor(self.config) if hasattr(GoldPredictor, '__init__') else None
        self.risk_manager = RiskManager(self.config) if hasattr(RiskManager, '__init__') else None
        self.mt5_connector = MT5Connector(self.config) if hasattr(MT5Connector, '__init__') else None
        
        self.is_initialized = False
        self.last_analysis: Optional[Dict] = None
        
    def _load_config(self) -> Dict[str, Any]:
        """تحميل الإعدادات من البيئة"""
        return {
            # MT5
            'MT5_LOGIN': os.getenv('MT5_LOGIN'),
            'MT5_PASSWORD': os.getenv('MT5_PASSWORD'),
            'MT5_SERVER': os.getenv('MT5_SERVER'),
            'MT5_PATH': os.getenv('MT5_PATH', 'C:\\Program Files\\MetaTrader 5\\terminal64.exe'),
            
            # الأصول
            'GOLD_SYMBOL': os.getenv('GOLD_SYMBOL', 'XAUUSD'),
            'DXY_SYMBOL': os.getenv('DXY_SYMBOL', 'DX1'),
            'SILVER_SYMBOL': os.getenv('SILVER_SYMBOL', 'XAGUSD'),
            'PLATINUM_SYMBOL': os.getenv('PLATINUM_SYMBOL', 'XPTUSD'),
            'PALLADIUM_SYMBOL': os.getenv('PALLADIUM_SYMBOL', 'XPDUSD'),
            'COPPER_SYMBOL': os.getenv('COPPER_SYMBOL', 'XCUUSD'),
            
            # التحليل
            'ENABLE_DXY_ANALYSIS': os.getenv('ENABLE_DXY_ANALYSIS', 'true').lower() == 'true',
            'ENABLE_SILVER_CORRELATION': os.getenv('ENABLE_SILVER_CORRELATION', 'true').lower() == 'true',
            'CORR_WINDOW_SHORT': int(os.getenv('CORR_WINDOW_SHORT', 10)),
            'CORR_WINDOW_MEDIUM': int(os.getenv('CORR_WINDOW_MEDIUM', 20)),
            'CORR_WINDOW_LONG': int(os.getenv('CORR_WINDOW_LONG', 50)),
            
            # الاستراتيجية
            'MIN_CONFIDENCE': float(os.getenv('MIN_CONFIDENCE', 0.65)),
            'MAX_CORRELATION_BOOST': float(os.getenv('MAX_CORRELATION_BOOST', 0.20)),
            
            # المخاطر
            'RISK_PERCENT': float(os.getenv('RISK_PERCENT', 1.0)),
            'MAX_DRAWDOWN': float(os.getenv('MAX_DRAWDOWN', 10.0)),
            'MAX_POSITIONS': int(os.getenv('MAX_POSITIONS', 3)),
            
            # النظام
            'TIMEFRAME': os.getenv('TIMEFRAME', 'H1'),
            'LOOKBACK_BARS': int(os.getenv('LOOKBACK_BARS', 1000)),
            'MODEL_PATH': os.getenv('MODEL_PATH', 'models/gold_predictor.pkl')
        }
    
    def initialize(self) -> bool:
        """تهيئة النظام"""
        try:
            logger.info("جاري تهيئة النظام...")
            
            # تهيئة جامع البيانات
            self.data_collector = MultiAssetDataCollector(self.config)
            if not self.data_collector.initialize_mt5():
                logger.error("فشل الاتصال بـ MT5")
                return False
            
            # تهيئة MT5 Connector إذا كان متوفراً
            if self.mt5_connector:
                self.mt5_connector.connect()
            
            self.is_initialized = True
            logger.info("تم تهيئة النظام بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في التهيئة: {e}")
            return False
    
    def shutdown(self):
        """إيقاف النظام"""
        if self.data_collector:
            self.data_collector.shutdown()
        if self.mt5_connector:
            self.mt5_connector.disconnect()
        self.is_initialized = False
        logger.info("تم إيقاف النظام")
    
    def fetch_market_data(self) -> Dict[str, pd.DataFrame]:
        """جلب البيانات السوقية"""
        if not self.is_initialized:
            raise RuntimeError("النظام غير مهيأ")
        
        data = self.data_collector.fetch_all_assets()
        
        if 'gold' not in data:
            raise ValueError("بيانات الذهب غير متوفرة")
        
        return data
    
    def analyze_technical(self, gold_data: pd.DataFrame) -> Dict:
        """
        التحليل الفني الأساسي للذهب
        """
        features = self.feature_engineer.create_base_features(gold_data)
        features = self.feature_engineer.add_momentum_features(features)
        features = self.feature_engineer.add_price_action_features(features)
        
        # تحليل الاتجاه
        last_close = gold_data['close'].iloc[-1]
        ema_20 = features['ema_20'].iloc[-1]
        ema_50 = features['ema_50'].iloc[-1]
        rsi = features['rsi_14'].iloc[-1]
        
        trend = 'NEUTRAL'
        if last_close > ema_20 > ema_50:
            trend = 'BULLISH'
        elif last_close < ema_20 < ema_50:
            trend = 'BEARISH'
        
        # إشارة الدخول
        signal = 'HOLD'
        confidence = 0.5
        
        if trend == 'BULLISH' and rsi < 70:
            signal = 'BUY'
            confidence = 0.6 + (70 - rsi) / 100
        elif trend == 'BEARISH' and rsi > 30:
            signal = 'SELL'
            confidence = 0.6 + (rsi - 30) / 100
        
        # مستويات الدعم والمقاومة
        support = gold_data['low'].tail(20).min()
        resistance = gold_data['high'].tail(20).max()
        
        return {
            'action': signal,
            'confidence': round(min(confidence, 0.9), 2),
            'trend': trend,
            'current_price': last_close,
            'entry': last_close,
            'stop_loss': support * 0.995 if signal == 'BUY' else resistance * 1.005,
            'take_profit': resistance * 1.01 if signal == 'BUY' else support * 0.99,
            'rsi': rsi,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'support': support,
            'resistance': resistance
        }
    
    def analyze_smc(self, gold_data: pd.DataFrame) -> Optional[Dict]:
        """
        تحليل Smart Money Concepts
        """
        if not self.smc_analyzer:
            return None
        
        try:
            return self.smc_analyzer.analyze(gold_data)
        except Exception as e:
            logger.warning(f"خطأ في تحليل SMC: {e}")
            return None
    
    def analyze_correlation(self, 
                           gold_data: pd.DataFrame,
                           market_data: Dict[str, pd.DataFrame]) -> Optional[CorrelationSignal]:
        """
        تحليل الارتباطات مع DXY
        """
        if not self.config['ENABLE_DXY_ANALYSIS']:
            return None
        
        if 'dollar_index' not in market_data:
            logger.warning("DXY غير متوفر")
            return None
        
        dxy_data = market_data['dollar_index']
        silver_data = market_data.get('silver')
        
        signal = self.correlation_analyzer.generate_correlation_signal(
            gold_data, dxy_data, silver_data
        )
        
        return signal
    
    def make_trading_decision(self, 
                               technical: Dict,
                               correlation: Optional[CorrelationSignal],
                               smc: Optional[Dict]) -> TradingDecision:
        """
        اتخاذ قرار التداول النهائي
        """
        if correlation:
            decision = self.correlation_strategy.combine_signals(
                gold_signal=technical,
                correlation_signal=correlation,
                smc_signal=smc
            )
        else:
            # بدون DXY
            decision = TradingDecision(
                action=technical['action'],
                confidence=technical['confidence'],
                position_size_multiplier=1.0,
                stop_loss_adjustment=0.0,
                take_profit_adjustment=0.0,
                reasoning="قرار بناءً على التحليل الفني فقط"
            )
        
        # فلترة المخاطر
        if self.risk_manager:
            should_block = self.risk_manager.evaluate_trade(decision)
            if should_block:
                decision.action = 'HOLD'
                decision.reasoning += " | محظور بواسطة إدارة المخاطر"
        
        return decision
    
    def execute_trade(self, decision: TradingDecision) -> Dict:
        """
        تنفيذ الصفقة عبر MT5
        """
        if not self.mt5_connector or decision.action == 'HOLD':
            return {'status': 'no_trade', 'reason': decision.reasoning}
        
        try:
            result = self.mt5_connector.send_order(
                symbol=self.config['GOLD_SYMBOL'],
                action=decision.action,
                volume=self.calculate_position_size(decision),
                slippage=10
            )
            return result
        except Exception as e:
            logger.error(f"خطأ في التنفيذ: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def calculate_position_size(self, decision: TradingDecision) -> float:
        """
        حساب حجم المركز
        """
        base_risk = self.config['RISK_PERCENT'] / 100
        adjusted_risk = base_risk * decision.position_size_multiplier
        
        # حساب اللوت بناءً على الرصيد
        if self.mt5_connector:
            balance = self.mt5_connector.get_account_balance()
            risk_amount = balance * adjusted_risk
            
            # افتراض وقف 50 نقطة
            pip_value = 10  # لـ XAUUSD
            stop_pips = 50
            
            lots = risk_amount / (stop_pips * pip_value)
            return round(max(0.01, min(lots, 10.0)), 2)
        
        return 0.1
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        تشغيل التحليل الكامل
        """
        if not self.is_initialized:
            if not self.initialize():
                return {'error': 'فشل التهيئة'}
        
        try:
            # 1. جلب البيانات
            logger.info("جلب البيانات...")
            market_data = self.fetch_market_data()
            gold_data = market_data['gold']
            
            # 2. التحليل الفني
            logger.info("التحليل الفني...")
            technical = self.analyze_technical(gold_data)
            
            # 3. تحليل SMC
            logger.info("تحليل SMC...")
            smc = self.analyze_smc(gold_data)
            
            # 4. تحليل الارتباطات
            logger.info("تحليل الارتباطات...")
            correlation = self.analyze_correlation(gold_data, market_data)
            
            # 5. اتخاذ القرار
            logger.info("اتخاذ القرار...")
            decision = self.make_trading_decision(technical, correlation, smc)
            
            # 6. تنفيذ (اختياري)
            execution = None
            if os.getenv('AUTO_TRADE', 'false').lower() == 'true':
                execution = self.execute_trade(decision)
            
            # 7. تجميع النتائج
            result = {
                'timestamp': datetime.now().isoformat(),
                'market_data': {
                    'gold_price': technical['current_price'],
                    'dxy_price': market_data.get('dollar_index', {}).get('close', pd.Series([0])).iloc[-1] if 'dollar_index' in market_data else None,
                    'silver_price': market_data.get('silver', {}).get('close', pd.Series([0])).iloc[-1] if 'silver' in market_data else None,
                },
                'technical_analysis': technical,
                'correlation_analysis': {
                    'enabled': self.config['ENABLE_DXY_ANALYSIS'],
                    'signal': {
                        'correlation': round(correlation.correlation, 3) if correlation else None,
                        'dxy_trend': correlation.dxy_trend if correlation else None,
                        'divergence': correlation.divergence.value if correlation else None,
                        'recommendation': correlation.recommendation if correlation else None,
                        'confidence_boost': round(correlation.confidence_boost, 3) if correlation else 0
                    } if correlation else None
                },
                'smc_analysis': smc,
                'trading_decision': {
                    'action': decision.action,
                    'confidence': round(decision.confidence, 2),
                    'position_size_multiplier': decision.position_size_multiplier,
                    'stop_loss_adjustment': decision.stop_loss_adjustment,
                    'take_profit_adjustment': decision.take_profit_adjustment,
                    'reasoning': decision.reasoning
                },
                'execution': execution
            }
            
            self.last_analysis = result
            logger.info(f"القرار: {decision.action} (الثقة: {decision.confidence})")
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في التحليل: {e}", exc_info=True)
            return {'error': str(e)}
    
    def get_status(self) -> Dict:
        """حالة النظام"""
        return {
            'initialized': self.is_initialized,
            'config': {
                'dxy_enabled': self.config['ENABLE_DXY_ANALYSIS'],
                'symbols': {
                    'gold': self.config['GOLD_SYMBOL'],
                    'dxy': self.config['DXY_SYMBOL'] if self.config['ENABLE_DXY_ANALYSIS'] else None,
                    'silver': self.config['SILVER_SYMBOL'] if self.config['ENABLE_SILVER_CORRELATION'] else None
                }
            },
            'last_analysis': self.last_analysis['timestamp'] if self.last_analysis else None
        }


# ============================================================
# إنشاء نسخة النظام
# ============================================================

system = GoldenAIPro()


# ============================================================
# Routes
# ============================================================

@app.route('/')
def index():
    return jsonify({
        'name': 'Golden AI Pro',
        'version': '2.0.0',
        'status': 'running',
        'dxy_integration': True
    })

@app.route('/api/status')
def status():
    return jsonify(system.get_status())

@app.route('/api/analyze', methods=['GET', 'POST'])
def analyze():
    """تشغيل تحليل كامل"""
    result = system.run_full_analysis()
    return jsonify(result)

@app.route('/api/signal')
def get_signal():
    """الحصول على الإشارة فقط"""
    if not system.is_initialized:
        system.initialize()
    
    try:
        market_data = system.fetch_market_data()
        technical = system.analyze_technical(market_data['gold'])
        correlation = system.analyze_correlation(market_data['gold'], market_data)
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'signal': technical['action'],
            'confidence': technical['confidence'],
            'price': technical['current_price'],
            'dxy_context': {
                'correlation': round(correlation.correlation, 2) if correlation else None,
                'dxy_trend': correlation.dxy_trend if correlation else None,
                'impact': correlation.confidence_boost if correlation else 0
            } if correlation else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-data')
def get_market_data():
    """جلب البيانات الخام"""
    try:
        if not system.is_initialized:
            system.initialize()
        
        data = system.fetch_market_data()
        
        # تحويل إلى JSON
        json_data = {}
        for key, df in data.items():
            json_data[key] = {
                'latest': {
                    'open': float(df['open'].iloc[-1]),
                    'high': float(df['high'].iloc[-1]),
                    'low': float(df['low'].iloc[-1]),
                    'close': float(df['close'].iloc[-1]),
                    'volume': int(df.get('volume', pd.Series([0])).iloc[-1]),
                    'time': df.index[-1].isoformat()
                },
                'change_24h': float(df['close'].pct_change(24).iloc[-1] * 100) if len(df) > 24 else 0
            }
        
        return jsonify(json_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/correlation')
def get_correlation():
    """حساب الارتباطات"""
    try:
        if not system.is_initialized:
            system.initialize()
        
        data = system.fetch_market_data()
        
        if len(data) < 2:
            return jsonify({'error': 'بيانات غير كافية'})
        
        corr_matrix = system.data_collector.get_correlation_matrix(data)
        
        # تحويل إلى dict
        corr_dict = {}
        if not corr_matrix.empty:
            for i in corr_matrix.index.levels[0]:
                corr_dict[str(i)] = corr_matrix.loc[i].to_dict()
        
        return jsonify({
            'correlation_matrix': corr_dict,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade', methods=['POST'])
def execute_trade():
    """تنفيذ صفقة يدوية"""
    try:
        data = request.json
        action = data.get('action', 'BUY')
        volume = data.get('volume', 0.1)
        
        if not system.mt5_connector:
            return jsonify({'error': 'MT5 غير متصل'}), 400
        
        result = system.mt5_connector.send_order(
            symbol=system.config['GOLD_SYMBOL'],
            action=action,
            volume=volume
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """سجل التحليلات"""
    # يمكن ربطه بقاعدة بيانات
    return jsonify({
        'last_analysis': system.last_analysis
    })

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """إدارة الإعدادات"""
    if request.method == 'GET':
        # إخفاء البيانات الحساسة
        safe_config = {k: v for k, v in system.config.items() 
                      if 'password' not in k.lower()}
        return jsonify(safe_config)
    
    elif request.method == 'POST':
        # تحديث الإعدادات
        new_config = request.json
        for key, value in new_config.items():
            if key in system.config:
                system.config[key] = value
        
        return jsonify({'status': 'updated', 'config': system.config})


# ============================================================
# التشغيل
# ============================================================

def run_server(host='0.0.0.0', port=5000, debug=False):
    """تشغيل الخادم"""
    # إنشاء مجلد اللوجات
    Path('logs').mkdir(exist_ok=True)
    
    # تهيئة النظام
    if not system.initialize():
        logger.error("فشل تهيئة النظام")
        return
    
    try:
        app.run(host=host, port=port, debug=debug)
    finally:
        system.shutdown()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Golden AI Pro Trading System')
    parser.add_argument('--host', default='0.0.0.0', help='عنوان الاستضافة')
    parser.add_argument('--port', type=int, default=5000, help='المنفذ')
    parser.add_argument('--debug', action='store_true', help='وضع التصحيح')
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, debug=args.debug)
