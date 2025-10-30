from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data_ingestion.polygon_client import PolygonDataClient
from backtester.engine import run_backtest
from backtester.strategies.sma_crossover import SmaCross


router = APIRouter()
_data_client: Optional[PolygonDataClient] = None


def _client() -> PolygonDataClient:
    global _data_client
    if _data_client is None:
        _data_client = PolygonDataClient()
    return _data_client


class BacktestRequest(BaseModel):
    ticker: str = Field(..., examples=["AAPL", "MSFT"])
    start_date: str = Field(..., examples=["2023-01-01"])
    end_date: str = Field(..., examples=["2023-12-31"])
    cash: float = 10000.0
    commission: float = 0.001
    fast_length: int = 10
    slow_length: int = 50


@router.post("/sma-crossover")
def backtest_sma_crossover(req: BacktestRequest):
    try:
        data = _client().get_daily_bars(req.ticker, req.start_date, req.end_date)
        if data.empty:
            raise HTTPException(status_code=404, detail="No data found for the given ticker and date range.")

        class ParamSmaCross(SmaCross):
            params = ("fast_length", req.fast_length), ("slow_length", req.slow_length)

        results = run_backtest(ParamSmaCross, data, cash=req.cash, commission=req.commission)
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
