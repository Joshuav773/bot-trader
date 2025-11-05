import backtrader as bt
import pandas as pd
from typing import Type, Dict, Any, Optional, List
from backtester.metrics import calculate_comprehensive_metrics, StrategyMetrics
from backtester.cost_model import DynamicSlippage, MarketImpactSlippage, EliteCommission


def run_backtest(
    strategy_class: Type[bt.Strategy],
    data: pd.DataFrame,
    cash: float = 10000.0,
    commission: float = 0.001,
    ticker: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initialize and run a backtest using the Backtrader engine.

    Args:
        strategy_class: The Backtrader strategy class to test.
        data: OHLCV DataFrame indexed by datetime with columns Open,High,Low,Close,Volume.
        cash: Initial cash.
        commission: Commission rate per trade.
        ticker: Optional ticker symbol, passed to strategy for news/external data.

    Returns:
        Dict with start and end portfolio values and PnL.
    """
    if data.empty:
        return {"start_portfolio_value": cash, "end_portfolio_value": cash, "pnl": 0.0}

    # Validate and clean data
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing_cols = [col for col in required_columns if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Ensure datetime index
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("Data index must be a DatetimeIndex")
    
    # Drop rows with NaN values in critical columns
    data = data[required_columns].copy()
    data = data.dropna(subset=required_columns)
    
    if data.empty:
        return {"start_portfolio_value": cash, "end_portfolio_value": cash, "pnl": 0.0}
    
    # Ensure data is sorted by datetime
    data = data.sort_index()
    
    # Ensure all values are numeric
    for col in required_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # Drop any rows that became NaN after conversion
    data = data.dropna()
    
    if data.empty:
        return {"start_portfolio_value": cash, "end_portfolio_value": cash, "pnl": 0.0}
    
    # Calculate with whatever data we have - be transparent about limitations
    data_count = len(data)
    warnings = []
    
    # Warn if data is limited (but still try to calculate)
    if data_count < 50:
        warnings.append(f"Limited data: Only {data_count} bars available. Indicators may not fully initialize. Results may be unreliable.")
    elif data_count < 100:
        warnings.append(f"Moderate data: {data_count} bars available. Some indicators may take time to stabilize.")
    
    # Get date range for transparency
    date_range = {
        "start": str(data.index.min()) if not data.empty else None,
        "end": str(data.index.max()) if not data.empty else None,
        "bars_count": data_count
    }

    try:
        cerebro = bt.Cerebro()
        
        # Add strategy with ticker as a parameter if needed
        if ticker:
            # Create a wrapper that sets ticker after initialization
            class StrategyWithTicker(strategy_class):
                def __init__(self):
                    super().__init__()
                    self.ticker = ticker
            cerebro.addstrategy(StrategyWithTicker)
        else:
            cerebro.addstrategy(strategy_class)

        # Configure PandasData feed - backtrader will use the index as datetime
        # and match column names automatically
        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed)

        cerebro.broker.setcash(cash)
        cerebro.broker.setcommission(commission=commission)

        start_portfolio_value = cerebro.broker.getvalue()
        cerebro.run()
        end_portfolio_value = cerebro.broker.getvalue()
        
        # Calculate percentage return
        pnl_pct = ((end_portfolio_value - start_portfolio_value) / start_portfolio_value) * 100 if start_portfolio_value > 0 else 0.0

        result = {
            "start_portfolio_value": start_portfolio_value,
            "end_portfolio_value": end_portfolio_value,
            "pnl": end_portfolio_value - start_portfolio_value,
            "pnl_percentage": round(pnl_pct, 2),
            "data_info": date_range,
            "warnings": warnings if warnings else None,
        }
        
        return result
    except Exception as e:
        # Include data info in error for transparency
        error_msg = f"Backtest execution failed: {str(e)}"
        if data_count < 50:
            error_msg += f" (Limited data: {data_count} bars may not be enough for this strategy)"
        raise RuntimeError(error_msg) from e
