"""
محرك Smart Money Concepts المتقدم
Advanced SMC Analysis Engine
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from loguru import logger

from .market_structure import MarketStructureAnalyzer
from .order_blocks import OrderBlockDetector
from .fair_value_gaps import FVGDetector
from .liquidity import LiquidityAnalyzer
from .kill_zones import KillZoneDetector


class SignalType(Enum):
    """أنواع الإشارات"""
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


@dataclass
class SMCSignal:
    """إشارة SMC"""
    type: SignalType
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timeframe: str
    timestamp: pd.Timestamp
    
    # SMC Components
    market_structure: Dict = field(default_factory=dict)
    order_blocks: List[Dict] = field(default_factory=list)
    fvgs: List[Dict] = field(default_factory=list)
    liquidity_levels: List[Dict] = field(default_factory=list)
    
    # Metadata
    risk_reward: float = 0.0
    position_size: float = 0.0
    
    def __post_init__(self):
        if self.stop_loss != 0:
            self.risk_reward = abs(self.take_profit - self.entry_price) / abs(self.entry_price - self.stop_loss)


class SMCEngine:
    """
    محرك SMC متكامل يجمع جميع مكونات التحليل
    """
    
    def __init__(self):
        self.market_structure = MarketStructureAnalyzer()
        self.order_blocks = OrderBlockDetector()
        self.fvgs = FVGDetector()
        self.liquidity = LiquidityAnalyzer()
        self.kill_zones = KillZoneDetector()
        
        self.min_confidence = 0.65
        
    def analyze(self, df: pd.DataFrame, timeframe: str = "H1") -> SMCSignal:
        """
        تحليل شامل للبيانات وإنشاء إشارة
        """
        if len(df) < 50:
            return SMCSignal(
                type=SignalType.NEUTRAL,
                confidence=0.0,
                entry_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                timeframe=timeframe,
                timestamp=df.index[-1]
            )
        
        # 1. تحليل بنية السوق
        structure = self.market_structure.analyze(df)
        
        # 2. اكتشاف كتل الطلبات
        obs = self.order_blocks.detect(df, structure['swing_points'])
        
        # 3. اكتشاف فجوات القيمة العادلة
        fvgs = self.fvgs.detect(df)
        
        # 4. تحليل السيولة
        liquidity = self.liquidity.analyze(df, structure['swing_points'])
        
        # 5. التحقق من منطقة الكيل
        in_kill_zone = self.kill_zones.is_in_kill_zone(df.index[-1])
        
        # 6. توليد الإشارة
        signal = self._generate_signal(
            df, structure, obs, fvgs, liquidity, in_kill_zone, timeframe
        )
        
        return signal
    
    def _generate_signal(
        self,
        df: pd.DataFrame,
        structure: Dict,
        obs: List[Dict],
        fvgs: List[Dict],
        liquidity: Dict,
        in_kill_zone: bool,
        timeframe: str
    ) -> SMCSignal:
        """توليد الإشارة بناءً على التحليل"""
        
        current_price = df['close'].iloc[-1]
        trend = structure.get('trend', 'neutral')
        bos = structure.get('bos', [])
        choch = structure.get('choch', [])
        
        # حساب النقاط
        atr = self._calculate_atr(df)
        
        # تحليل الاتجاه والإشارة
        signal_type = SignalType.NEUTRAL
        confidence = 0.0
        entry = current_price
        sl = 0.0
        tp = 0.0
        
        # منطق الشراء
        if trend == "bullish" and in_kill_zone:
            # البحث عن كتلة طلبات صاعدة
            bullish_obs = [ob for ob in obs if ob['type'] == 'bullish' and ob['active']]
            
            if bullish_obs and fvgs:
                # أعلى كتلة طلبات صاعدة
                best_ob = min(bullish_obs, key=lambda x: abs(x['bottom'] - current_price))
                
                # التحقق من السعر بالقرب من كتلة الطلبات
                if abs(best_ob['bottom'] - current_price) < atr * 2:
                    signal_type = SignalType.BUY
                    entry = current_price
                    sl = best_ob['bottom'] - atr * 1.5
                    tp = current_price + (current_price - sl) * 2  # 1:2 RR
                    
                    # حساب الثقة
                    confidence = self._calculate_confidence(
                        trend="bullish",
                        has_ob=True,
                        has_fvg=len([f for f in fvgs if f['type'] == 'bullish']) > 0,
                        liquidity_swept=liquidity.get('swept_lows', False),
                        in_kill_zone=in_kill_zone,
                        bos=len(bos) > 0,
                        choch=len(choch) > 0
                    )
        
        # منطق البيع
        elif trend == "bearish" and in_kill_zone:
            bearish_obs = [ob for ob in obs if ob['type'] == 'bearish' and ob['active']]
            
            if bearish_obs and fvgs:
                best_ob = min(bearish_obs, key=lambda x: abs(x['top'] - current_price))
                
                if abs(best_ob['top'] - current_price) < atr * 2:
                    signal_type = SignalType.SELL
                    entry = current_price
                    sl = best_ob['top'] + atr * 1.5
                    tp = current_price - (sl - current_price) * 2
                    
                    confidence = self._calculate_confidence(
                        trend="bearish",
                        has_ob=True,
                        has_fvg=len([f for f in fvgs if f['type'] == 'bearish']) > 0,
                        liquidity_swept=liquidity.get('swept_highs', False),
                        in_kill_zone=in_kill_zone,
                        bos=len(bos) > 0,
                        choch=len(choch) > 0
                    )
        
        return SMCSignal(
            type=signal_type,
            confidence=confidence,
            entry_price=round(entry, 2),
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
            timeframe=timeframe,
            timestamp=df.index[-1],
            market_structure=structure,
            order_blocks=obs,
            fvgs=fvgs,
            liquidity_levels=liquidity.get('levels', [])
        )
    
    def _calculate_confidence(
        self,
        trend: str,
        has_ob: bool,
        has_fvg: bool,
        liquidity_swept: bool,
        in_kill_zone: bool,
        bos: bool,
        choch: bool
    ) -> float:
        """حساب درجة الثقة في الإشارة"""
        score = 0.0
        
        # Trend alignment (30%)
        if trend in ["bullish", "bearish"]:
            score += 0.30
        
        # Order Block present (25%)
        if has_ob:
            score += 0.25
        
        # FVG present (20%)
        if has_fvg:
            score += 0.20
        
        # Liquidity swept (15%)
        if liquidity_swept:
            score += 0.15
        
        # Kill zone (10%)
        if in_kill_zone:
            score += 0.10
        
        # BOS/CHoCH bonus (up to 10%)
        if bos:
            score += 0.05
        if choch:
            score += 0.05
        
        return min(score, 1.0)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """حساب Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else (high - low).mean()
    
    def multi_timeframe_analysis(
        self,
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, SMCSignal]:
        """
        تحليل متعدد الأطر الزمنية
        """
        signals = {}
        
        for timeframe, df in data_dict.items():
            signals[timeframe] = self.analyze(df, timeframe)
        
        # تجميع الإشارات
        aligned_signals = self._check_timeframe_alignment(signals)
        
        return aligned_signals
    
    def _check_timeframe_alignment(self, signals: Dict[str, SMCSignal]) -> Dict[str, SMCSignal]:
        """التحقق من توافق الإشارات عبر الأطر الزمنية"""
        # منطق التوافق: إذا كانت الإشارات متفقة في H4 و H1، نرفع الثقة
        # إذا كانت متضاربة، نخفض الثقة
        
        h4_signal = signals.get('H4')
        h1_signal = signals.get('H1')
        
        if h4_signal and h1_signal:
            if h4_signal.type == h1_signal.type and h4_signal.type != SignalType.NEUTRAL:
                # رفع الثقة في الإشارة الأقل إطاراً
                h1_signal.confidence = min(h1_signal.confidence * 1.2, 1.0)
                h1_signal.timeframe = "H1 (H4 Aligned)"
        
        return signals
