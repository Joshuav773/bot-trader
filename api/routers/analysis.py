from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data_ingestion.polygon_client import PolygonDataClient
from analysis_engine.candlestick_patterns import detect_hammer
from analysis_engine.indicators import compute_sma, compute_rsi


router = APIRouter()
_client = PolygonDataClient()


class AnalysisRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    sma_length: int = 20
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
