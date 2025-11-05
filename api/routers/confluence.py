from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from data_ingestion.polygon_client import PolygonDataClient
from backtester.engine import run_backtest
from backtester.strategies.confluence import ConfluenceStrategy


router = APIRouter()


class ConfluenceBacktestRequest(BaseModel):
    ticker: str = Field(..., examples=["AAPL"])
    start_date: str = Field(..., examples=["2023-01-01"])
    end_date: str = Field(..., examples=["2023-12-31"])
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.001
    fast_ma: int = 10
    slow_ma: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    volume_ma_period: int = 20
    volume_threshold: float = 1.2
    require_candlestick: bool = True
    require_news: bool = True
    news_sentiment_threshold: float = 0.1
    news_days_back: int = 7
    min_confirmations: int = 3


class ConfluenceOptimizeRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.001
    # Parameter ranges to test
    fast_ma_range: List[int] = Field(default=[5, 10, 15, 20])
    slow_ma_range: List[int] = Field(default=[30, 50, 100])
    rsi_oversold_range: List[float] = Field(default=[25.0, 30.0, 35.0])
    rsi_overbought_range: List[float] = Field(default=[65.0, 70.0, 75.0])
    min_confirmations_range: List[int] = Field(default=[2, 3, 4])


@router.post("/backtest")
def backtest_confluence(req: ConfluenceBacktestRequest) -> Dict[str, Any]:
    """Backtest a confluence strategy with specific parameters."""
    try:
        client = PolygonDataClient()
        data = client.get_bars(req.ticker, req.start_date, req.end_date, timeframe=req.timeframe)
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {req.ticker} on {req.timeframe} timeframe for the given date range.")
        
        class ParamConfluence(ConfluenceStrategy):
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
        
        results = run_backtest(ParamConfluence, data, cash=req.cash, commission=req.commission, ticker=req.ticker)
        
        # Calculate additional metrics
        pnl_pct = ((results["end_portfolio_value"] - results["start_portfolio_value"]) / results["start_portfolio_value"]) * 100
        
        return {
            **results,
            "pnl_percentage": round(pnl_pct, 2),
            "parameters": {
                "fast_ma": req.fast_ma,
                "slow_ma": req.slow_ma,
                "rsi_period": req.rsi_period,
                "min_confirmations": req.min_confirmations,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize")
def optimize_confluence(req: ConfluenceOptimizeRequest) -> Dict[str, Any]:
    """
    Train/optimize confluence strategy by testing parameter combinations.
    Returns the best performing configuration.
    """
    try:
        client = PolygonDataClient()
        data = client.get_bars(req.ticker, req.start_date, req.end_date, timeframe=req.timeframe)
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {req.ticker} on {req.timeframe} timeframe for the given date range.")
        
        best_result = None
        best_params = None
        best_pnl_pct = float("-inf")
        all_results = []
        
        # Grid search over parameter combinations
        total_combos = (
            len(req.fast_ma_range) *
            len(req.slow_ma_range) *
            len(req.rsi_oversold_range) *
            len(req.rsi_overbought_range) *
            len(req.min_confirmations_range)
        )
        
        combo_num = 0
        for fast_ma in req.fast_ma_range:
            for slow_ma in req.slow_ma_range:
                if fast_ma >= slow_ma:
                    continue  # Skip invalid combinations
                for rsi_oversold in req.rsi_oversold_range:
                    for rsi_overbought in req.rsi_overbought_range:
                        if rsi_oversold >= rsi_overbought:
                            continue
                        for min_conf in req.min_confirmations_range:
                            combo_num += 1
                            
                            class ParamConfluence(ConfluenceStrategy):
                                params = (
                                    ("fast_ma", fast_ma),
                                    ("slow_ma", slow_ma),
                                    ("rsi_period", 14),
                                    ("rsi_oversold", rsi_oversold),
                                    ("rsi_overbought", rsi_overbought),
                                    ("volume_ma_period", 20),
                                    ("volume_threshold", 1.2),
                                    ("require_candlestick", False),
                                    ("min_confirmations", min_conf),
                                )
                            
                            try:
                                result = run_backtest(ParamConfluence, data, cash=req.cash, commission=req.commission)
                                pnl_pct = ((result["end_portfolio_value"] - result["start_portfolio_value"]) / result["start_portfolio_value"]) * 100
                                
                                params_dict = {
                                    "fast_ma": fast_ma,
                                    "slow_ma": slow_ma,
                                    "rsi_oversold": rsi_oversold,
                                    "rsi_overbought": rsi_overbought,
                                    "min_confirmations": min_conf,
                                }
                                
                                all_results.append({
                                    "parameters": params_dict,
                                    "pnl_percentage": round(pnl_pct, 2),
                                    "end_portfolio_value": result["end_portfolio_value"],
                                })
                                
                                if pnl_pct > best_pnl_pct:
                                    best_pnl_pct = pnl_pct
                                    best_result = result
                                    best_params = params_dict
                            except Exception as e:
                                # Skip failed combinations
                                continue
        
        if best_result is None:
            raise HTTPException(status_code=400, detail="No valid parameter combinations found")
        
        # Sort all results by PnL
        all_results.sort(key=lambda x: x["pnl_percentage"], reverse=True)
        
        return {
            "best_parameters": best_params,
            "best_result": {
                **best_result,
                "pnl_percentage": round(best_pnl_pct, 2),
            },
            "top_10_results": all_results[:10],
            "total_combinations_tested": combo_num,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

