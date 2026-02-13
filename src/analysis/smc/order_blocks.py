"""
اكتشاف كتل الطلبات (Order Blocks)
Order Block Detection with mitigation tracking
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class OrderBlock:
    """كتلة طلبات"""
    index: int
    top: float
    bottom: float
    type: str  # "bullish" or "bearish"
    volume: float
    timestamp: pd.Timestamp
    active: bool = True
    mitigation_index: Optional[int] = None


class OrderBlockDetector:
    """
    كاشف كتل الطلبات مع:
    - اكتشاف Bullish/Bearish OBs
    - تتبع الـ Mitigation
    - تصفية حسب القوة
    """
    
    def __init__(
        self,
        min_candles: int = 3,
        max_candles: int = 10,
        min_volume_percentile: float = 70.0
    ):
        self.min_candles = min_candles
        self.max_candles = max_candles
        self.min_volume_percentile = min_volume_percentile
        
    def detect(
        self,
        df: pd.DataFrame,
        swing_points: List[Dict]
    ) -> List[Dict]:
        """
        اكتشاف كتل الطلبات
        """
        order_blocks = []
        
        # حساب percentiles الحجم
        volume_threshold = np.percentile(df['volume'], self.min_volume_percentile)
        
        # البحث عن كتل صاعدة (قبل قمم)
        bullish_obs = self._find_bullish_obs(df, swing_points, volume_threshold)
        
        # البحث عن كتل هابطة (قبل قيعان)
        bearish_obs = self._find_bearish_obs(df, swing_points, volume_threshold)
        
        # دمج النتائج
        all_obs = bullish_obs + bearish_obs
        
        # تتبع الـ Mitigation
        all_obs = self._track_mitigation(df, all_obs)
        
        # تحويل إلى قوائم
        return [self._ob_to_dict(ob) for ob in all_obs]
    
    def _find_bullish_obs(
        self,
        df: pd.DataFrame,
        swing_points: List[Dict],
        volume_threshold: float
    ) -> List[OrderBlock]:
        """اكتشاف كتل الطلبات الصاعدة"""
        obs = []
        swing_highs = [sp for sp in swing_points if sp['type'] == 'high']
        
        for swing in swing_highs:
            swing_idx = swing['index']
            
            # البحث عن آخر شمعة هابطة قبل القمة
            for i in range(max(0, swing_idx - self.max_candles), swing_idx - self.min_candles + 1):
                candle = df.iloc[i]
                next_candle = df.iloc[i + 1] if i + 1 < len(df) else None
                
                # شمعة هابطة قوية
                if candle['close'] < candle['open']:  # هابطة
                    body_size = abs(candle['close'] - candle['open'])
                    wick_size = candle['high'] - candle['open']
                    
                    # شمعة قوية مع حجم كبير
                    if body_size > wick_size * 0.5 and candle['volume'] > volume_threshold:
                        # التحقق من الارتداد بعدها
                        if next_candle is not None and next_candle['close'] > candle['close']:
                            ob = OrderBlock(
                                index=i,
                                top=candle['high'],
                                bottom=candle['low'],
                                type='bullish',
                                volume=candle['volume'],
                                timestamp=df.index[i]
                            )
                            obs.append(ob)
                            break
        
        return obs
    
    def _find_bearish_obs(
        self,
        df: pd.DataFrame,
        swing_points: List[Dict],
        volume_threshold: float
    ) -> List[OrderBlock]:
        """اكتشاف كتل الطلبات الهابطة"""
        obs = []
        swing_lows = [sp for sp in swing_points if sp['type'] == 'low']
        
        for swing in swing_lows:
            swing_idx = swing['index']
            
            # البحث عن آخر شمعة صاعدة قبل القاع
            for i in range(max(0, swing_idx - self.max_candles), swing_idx - self.min_candles + 1):
                candle = df.iloc[i]
                next_candle = df.iloc[i + 1] if i + 1 < len(df) else None
                
                # شمعة صاعدة قوية
                if candle['close'] > candle['open']:  # صاعدة
                    body_size = abs(candle['close'] - candle['open'])
                    wick_size = candle['close'] - candle['low']
                    
                    # شمعة قوية مع حجم كبير
                    if body_size > wick_size * 0.5 and candle['volume'] > volume_threshold:
                        # التحقق من الارتداد بعدها
                        if next_candle is not None and next_candle['close'] < candle['close']:
                            ob = OrderBlock(
                                index=i,
                                top=candle['high'],
                                bottom=candle['low'],
                                type='bearish',
                                volume=candle['volume'],
                                timestamp=df.index[i]
                            )
                            obs.append(ob)
                            break
        
        return obs
    
    def _track_mitigation(
        self,
        df: pd.DataFrame,
        obs: List[OrderBlock]
    ) -> List[OrderBlock]:
        """تتبع الـ Mitigation للكتل"""
        for ob in obs:
            # البحث عن اختراق الكتلة
            for i in range(ob.index + 1, len(df)):
                candle = df.iloc[i]
                
                if ob.type == 'bullish':
                    # Mitigation: السعر يغلق أسفل الكتلة
                    if candle['close'] < ob.bottom:
                        ob.active = False
                        ob.mitigation_index = i
                        break
                    # Partial mitigation: لمس القاع
                    elif candle['low'] <= ob.bottom and candle['close'] >= ob.bottom:
                        ob.active = True  # ما زالت نشطة لكن ضعيفة
                
                elif ob.type == 'bearish':
                    # Mitigation: السعر يغلق أعلى الكتلة
                    if candle['close'] > ob.top:
                        ob.active = False
                        ob.mitigation_index = i
                        break
                    # Partial mitigation: لمس القمة
                    elif candle['high'] >= ob.top and candle['close'] <= ob.top:
                        ob.active = True
        
        return obs
    
    def _ob_to_dict(self, ob: OrderBlock) -> Dict:
        """تحويل الكتلة إلى قاموس"""
        return {
            'index': ob.index,
            'top': ob.top,
            'bottom': ob.bottom,
            'type': ob.type,
            'volume': ob.volume,
            'timestamp': ob.timestamp.isoformat(),
            'active': ob.active,
            'mitigation_index': ob.mitigation_index,
            'strength': self._calculate_ob_strength(ob)
        }
    
    def _calculate_ob_strength(self, ob: OrderBlock) -> float:
        """حساب قوة الكتلة"""
        strength = 1.0
        
        # الكتل النشطة أقوى
        if not ob.active:
            strength *= 0.5
        
        # الحجم الكبير = قوة أعلى (مبسط)
        # في التطبيق الحقيقي، قارن مع المتوسط المتحرك للحجم
        
        return strength
