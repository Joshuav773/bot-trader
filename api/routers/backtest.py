from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data_ingestion.polygon_client import PolygonDataClient
from backtester.engine import run_backtest
from backtester.advanced_engine import run_advanced_backtest
from backtester.strategies.sma_crossover import SmaCross
from backtester.strategies.bollinger_bands import BollingerBandsStrategy
from backtester.strategies.enhanced_sma import EnhancedSmaCrossover


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
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.001
    fast_length: int = 10
    slow_length: int = 50


class BollingerBandsRequest(BaseModel):
    ticker: str = Field(..., examples=["AAPL", "MSFT"])
    start_date: str = Field(..., examples=["2023-01-01"])
    end_date: str = Field(..., examples=["2023-12-31"])
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.001
    period: int = Field(default=20, description="Period for Bollinger Bands SMA")
    devfactor: float = Field(default=2.0, description="Number of standard deviations for bands")
    size: float = Field(default=0.95, description="Percentage of cash to use per trade (0-1)")


class AdvancedBacktestRequest(BaseModel):
    ticker: str = Field(..., examples=["AAPL", "MSFT"])
    start_date: str = Field(..., examples=["2023-01-01"])
    end_date: str = Field(..., examples=["2023-12-31"])
    timeframe: str = Field(default="1d", examples=["1d", "4h", "1h", "30m", "15m", "5m"])
    cash: float = 10000.0
    commission: float = 0.001
    fast_length: int = 10
    slow_length: int = 50
    use_advanced_slippage: bool = Field(default=True, description="Use dynamic slippage modeling")
    slippage_model: str = Field(default="dynamic", description="'dynamic', 'market_impact', or 'none'")
    max_drawdown_pct: float = Field(default=20.0, description="Maximum drawdown % before pausing")
    risk_per_trade: float = Field(default=0.02, description="Risk % per trade (2%)")


@router.post("/sma-crossover")
def backtest_sma_crossover(req: BacktestRequest):
    try:
        data = _client().get_bars(req.ticker, req.start_date, req.end_date, timeframe=req.timeframe)
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {req.ticker} on {req.timeframe} timeframe for the given date range.")

        class ParamSmaCross(SmaCross):
            params = ("fast_length", req.fast_length), ("slow_length", req.slow_length)

        results = run_backtest(ParamSmaCross, data, cash=req.cash, commission=req.commission, ticker=req.ticker)
        
        # Engine now returns pnl_percentage and data_info, so we just return results
        return results
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bollinger-bands")
def backtest_bollinger_bands(req: BollingerBandsRequest):
    """
    Backtest a Mean-Reversion strategy using Bollinger Bands.
    
    Strategy:
    - Buys when price touches lower band (oversold)
    - Sells when price touches upper band (overbought)
    - Assumes price will revert to the middle band (SMA)
    """
    try:
        data = _client().get_bars(req.ticker, req.start_date, req.end_date, timeframe=req.timeframe)
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {req.ticker} on {req.timeframe} timeframe for the given date range.")

        class ParamBollingerBands(BollingerBandsStrategy):
            params = (
                ("period", req.period),
                ("devfactor", req.devfactor),
                ("size", req.size),
            )

        results = run_backtest(ParamBollingerBands, data, cash=req.cash, commission=req.commission, ticker=req.ticker)
        
        return results
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhanced-sma")
def backtest_enhanced_sma(req: AdvancedBacktestRequest):
    """
    Enhanced SMA Crossover with advanced risk management:
    - Maximum drawdown protection
    - Risk-based position sizing
    - Volatility-adjusted entries
    - ATR-based stop losses
    - Dynamic slippage modeling
    """
    try:
        data = _client().get_bars(req.ticker, req.start_date, req.end_date, timeframe=req.timeframe)
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {req.ticker} on {req.timeframe} timeframe for the given date range.")

        class ParamEnhancedSma(EnhancedSmaCrossover):
            params = (
                ("fast_length", req.fast_length),
                ("slow_length", req.slow_length),
                ("max_drawdown_pct", req.max_drawdown_pct),
                ("risk_per_trade", req.risk_per_trade),
                ("use_volatility_adjustment", True),
            )

        results = run_advanced_backtest(
            strategy_class=ParamEnhancedSma,
            data=data,
            cash=req.cash,
            commission=req.commission,
            ticker=req.ticker,
            use_dynamic_slippage=req.use_advanced_slippage,
            slippage_model=req.slippage_model,
        )
        
        return results
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
