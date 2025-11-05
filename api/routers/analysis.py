from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np

from data_ingestion.polygon_client import PolygonDataClient
from analysis_engine.candlestick_patterns import detect_hammer
from analysis_engine.indicators import compute_sma, compute_ema, compute_rsi
from config.settings import POLYGON_DATA_LIMITS


router = APIRouter()
_client = PolygonDataClient()


class AnalysisRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    timeframe: str = "1d"
    sma_length: int = 20
    ema_length: int = 20
    rsi_length: int = 14


@router.post("/signals")
def analyze_signals(req: AnalysisRequest) -> Dict[str, Any]:
    try:
        df = _client.get_daily_bars(req.ticker, req.start_date, req.end_date)
        if df.empty:
            raise HTTPException(status_code=404, detail="No data for range")

        sma = compute_sma(df["Close"], length=req.sma_length)
        rsi = compute_rsi(df["Close"], length=req.rsi_length)
        hammer = detect_hammer(df)

        n = 5
        return {
            "sma": sma.tail(n).round(6).dropna().to_dict(),
            "rsi": rsi.tail(n).round(6).dropna().to_dict(),
            "hammer": {str(idx): bool(val) for idx, val in hammer.tail(n).items()},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-limits")
def get_data_limits() -> Dict[str, Any]:
    """
    Get current Polygon.io data limits per timeframe.
    These limits can be adjusted via environment variables for different API tiers.
    """
    return {
        "limits": POLYGON_DATA_LIMITS,
        "note": "Limits are in days of historical data available. Update via POLYGON_LIMIT_* environment variables.",
    }


@router.post("/chart")
def chart_data(req: AnalysisRequest) -> Dict[str, Any]:
    try:
        # Use get_bars with timeframe support
        df = _client.get_bars(req.ticker, req.start_date, req.end_date, timeframe=req.timeframe)
        if df.empty:
            # Provide helpful error message based on timeframe using dynamic limits
            tf_lower = req.timeframe.lower()
            # Normalize timeframe key
            tf_key = tf_lower
            if tf_key not in POLYGON_DATA_LIMITS:
                # Try to normalize
                if tf_key in ["4h", "4hour"]:
                    tf_key = "4h"
                elif tf_key in ["1h", "hour"]:
                    tf_key = "1h"
                elif tf_key in ["30m", "30min"]:
                    tf_key = "30m"
                elif tf_key in ["15m", "15min"]:
                    tf_key = "15m"
                elif tf_key in ["5m", "5min"]:
                    tf_key = "5m"
                elif tf_key in ["1d", "day"]:
                    tf_key = "1d"
            
            limit_days = POLYGON_DATA_LIMITS.get(tf_key, 730)
            
            if limit_days < 365:
                hint = f"{req.timeframe} data is limited to ~{limit_days} days. Try a shorter date range."
            elif limit_days < 730:
                hint = f"{req.timeframe} data is limited to ~{limit_days // 30} months. Try a shorter date range."
            else:
                hint = f"{req.timeframe} data is limited to ~{limit_days // 365} years."
            
            detail = f"No data found for {req.ticker} on {req.timeframe} timeframe for the given date range. {hint}".strip()
            raise HTTPException(status_code=404, detail=detail)
        sma = compute_sma(df["Close"], length=req.sma_length)
        ema = compute_ema(df["Close"], length=req.ema_length)
        rsi = compute_rsi(df["Close"], length=req.rsi_length)
        
        # Ensure indicators are aligned with the dataframe index
        sma = sma.reindex(df.index)
        ema = ema.reindex(df.index)
        rsi = rsi.reindex(df.index)
        
        idx = df.index.astype(str).tolist()
        
        # Convert to lists, handling NaN properly
        def to_list_with_nan(series: pd.Series) -> List[Any]:
            return [None if pd.isna(val) else float(val) for val in series]
        
        return {
            "index": idx,
            "open": df["Open"].astype(float).tolist(),
            "high": df["High"].astype(float).tolist(),
            "low": df["Low"].astype(float).tolist(),
            "close": df["Close"].astype(float).tolist(),
            "volume": df["Volume"].astype(float).tolist(),
            "sma": to_list_with_nan(sma),
            "ema": to_list_with_nan(ema),
            "rsi": to_list_with_nan(rsi),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
