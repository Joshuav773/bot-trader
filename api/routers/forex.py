from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from data_ingestion.polygon_client import PolygonDataClient
from backtester.engine import run_backtest
from backtester.strategies.forex_confluence import ForexConfluenceStrategy
from ml_models.forex_learning_agent import ForexLearningAgent, MAJOR_FOREX_PAIRS


router = APIRouter()


class ForexBacktestRequest(BaseModel):
    pair: str = Field(..., examples=["EURUSD", "GBPUSD"])
    start_date: str = Field(..., examples=["2023-01-01"])
    end_date: str = Field(..., examples=["2023-12-31"])
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.0001  # Typical forex commission (0.01%)
    fast_ma: int = 10
    slow_ma: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 25.0
    rsi_overbought: float = 75.0
    volume_ma_period: int = 20
    volume_threshold: float = 1.15
    require_candlestick: bool = True
    require_news: bool = True
    news_sentiment_threshold: float = 0.05
    news_days_back: int = 7
    min_confirmations: int = 3


class ForexOptimizeRequest(BaseModel):
    pair: str | None = None  # None = optimize all major pairs
    start_date: str
    end_date: str
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.0001


@router.post("/confluence/backtest")
def backtest_forex_confluence(req: ForexBacktestRequest) -> Dict[str, Any]:
    """Backtest confluence strategy for a forex pair."""
    try:
        client = PolygonDataClient()
        # Normalize forex pair
        if client.is_forex_ticker(req.pair):
            normalized_pair = client.normalize_forex_ticker(req.pair)
        else:
            normalized_pair = req.pair
        
        data = client.get_bars(normalized_pair, req.start_date, req.end_date, timeframe=req.timeframe)
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {req.pair} on {req.timeframe} timeframe for the given date range.")
        
        class ParamForex(ForexConfluenceStrategy):
            params = (
                ("fast_ma", req.fast_ma),
                ("slow_ma", req.slow_ma),
                ("rsi_period", req.rsi_period),
                ("rsi_oversold", req.rsi_oversold),
                ("rsi_overbought", req.rsi_overbought),
                ("volume_ma_period", req.volume_ma_period),
                ("volume_threshold", req.volume_threshold),
                ("require_candlestick", req.require_candlestick),
                ("require_news", req.require_news),
                ("news_sentiment_threshold", req.news_sentiment_threshold),
                ("news_days_back", req.news_days_back),
                ("min_confirmations", req.min_confirmations),
            )
        
        results = run_backtest(ParamForex, data, cash=req.cash, commission=req.commission, ticker=normalized_pair)
        pnl_pct = ((results["end_portfolio_value"] - results["start_portfolio_value"]) / results["start_portfolio_value"]) * 100
        
        return {
            **results,
            "pnl_percentage": round(pnl_pct, 2),
            "pair": req.pair,
            "parameters": {
                "fast_ma": req.fast_ma,
                "slow_ma": req.slow_ma,
                "rsi_oversold": req.rsi_oversold,
                "rsi_overbought": req.rsi_overbought,
                "min_confirmations": req.min_confirmations,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confluence/optimize")
def optimize_forex_confluence(req: ForexOptimizeRequest) -> Dict[str, Any]:
    """
    Forex Learning Agent: Optimize confluence strategy for forex markets.
    If pair is None, optimizes across all major pairs and returns aggregate recommendations.
    """
    try:
        agent = ForexLearningAgent()
        
        if req.pair:
            # Optimize single pair
            result = agent.optimize_pair(req.pair, req.start_date, req.end_date, timeframe=req.timeframe)
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            return result
        else:
            # Optimize all major pairs
            result = agent.optimize_all_majors(req.start_date, req.end_date, timeframe=req.timeframe)
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pairs")
def get_major_pairs() -> List[str]:
    """Get list of major forex pairs."""
    return MAJOR_FOREX_PAIRS

