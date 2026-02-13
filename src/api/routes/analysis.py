"""
مسارات التحليل
Analysis Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from src.analysis.smc.smc_engine import SMCEngine
from src.analysis.volume_profile.volume_profile import VolumeProfileAnalyzer
from src.data.connectors.mt5_connector import mt5_connector
from config.settings import settings

router = APIRouter(prefix="/analysis", tags=["analysis"])

smc_engine = SMCEngine()
vp_analyzer = VolumeProfileAnalyzer()


@router.post("/smc")
async def analyze_smc(timeframe: str = Query("H1", enum=["M1", "M5", "M15", "H1", "H4", "D1"])):
    """
    تحليل SMC
    """
    try:
        df = await mt5_connector.get_rates(settings.SYMBOL, timeframe, count=500)
        signal = smc_engine.analyze(df, timeframe)
        
        return {
            "signal": signal.type.value,
            "confidence": signal.confidence,
            "entry": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "components": {
                "order_blocks": len(signal.order_blocks),
                "fvgs": len(signal.fvgs),
                "liquidity_levels": len(signal.liquidity_levels)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/volume-profile")
async def analyze_volume_profile(timeframe: str = "H1"):
    """
    تحليل Volume Profile
    """
    try:
        df = await mt5_connector.get_rates(settings.SYMBOL, timeframe, count=200)
        vp = vp_analyzer.analyze(df)
        
        return vp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-timeframe")
async def multi_timeframe_analysis():
    """
    تحليل متعدد الأطر الزمنية
    """
    try:
        timeframes = ["H1", "H4", "D1"]
        results = {}
        
        for tf in timeframes:
            df = await mt5_connector.get_rates(settings.SYMBOL, tf, count=200)
            signal = smc_engine.analyze(df, tf)
            results[tf] = {
                "signal": signal.type.value,
                "confidence": signal.confidence
            }
        
        # التحقق من التوافق
        aligned = len(set(r['signal'] for r in results.values() if r['signal'] != 'neutral')) == 1
        
        return {
            "timeframes": results,
            "aligned": aligned,
            "recommendation": "trade" if aligned else "wait"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
