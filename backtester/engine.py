import backtrader as bt
import pandas as pd
from typing import Type, Dict, Any


def run_backtest(
    strategy_class: Type[bt.Strategy],
    data: pd.DataFrame,
    cash: float = 10000.0,
    commission: float = 0.001,
) -> Dict[str, Any]:
    """
    Initialize and run a backtest using the Backtrader engine.

    Args:
        strategy_class: The Backtrader strategy class to test.
        data: OHLCV DataFrame indexed by datetime with columns Open,High,Low,Close,Volume.
        cash: Initial cash.
        commission: Commission rate per trade.

    Returns:
        Dict with start and end portfolio values and PnL.
    """
    if data.empty:
        return {"start_portfolio_value": cash, "end_portfolio_value": cash, "pnl": 0.0}

    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)

    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)

    start_portfolio_value = cerebro.broker.getvalue()
    cerebro.run()
    end_portfolio_value = cerebro.broker.getvalue()

    return {
        "start_portfolio_value": start_portfolio_value,
        "end_portfolio_value": end_portfolio_value,
        "pnl": end_portfolio_value - start_portfolio_value,
    }
