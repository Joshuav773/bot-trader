"""
Enhanced Backtesting Engine with Advanced Metrics and Cost Modeling

Implements high-fidelity backtesting with:
- Dynamic slippage and market impact modeling
- Comprehensive risk metrics (Sharpe, MDD, Calmar, Alpha)
- Trade-level tracking and analysis
- Equity curve generation
"""
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Type, Dict, Any, Optional, List
from datetime import datetime

from backtester.metrics import calculate_comprehensive_metrics, StrategyMetrics
from backtester.cost_model import DynamicSlippage, MarketImpactSlippage, EliteCommission


def run_advanced_backtest(
    strategy_class: Type[bt.Strategy],
    data: pd.DataFrame,
    cash: float = 10000.0,
    commission: float = 0.001,
    ticker: Optional[str] = None,
    use_dynamic_slippage: bool = True,
    use_market_impact: bool = False,
    slippage_model: str = "dynamic",  # "dynamic", "market_impact", "none"
    benchmark_data: Optional[pd.DataFrame] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> Dict[str, Any]:
    """
    Enhanced backtest with comprehensive metrics and advanced cost modeling.
    
    Args:
        strategy_class: The Backtrader strategy class to test
        data: OHLCV DataFrame indexed by datetime
        cash: Initial cash
        commission: Commission rate per trade
        ticker: Optional ticker symbol
        use_dynamic_slippage: Enable dynamic slippage modeling
        use_market_impact: Enable market impact modeling
        slippage_model: "dynamic", "market_impact", or "none"
        benchmark_data: Optional benchmark for Alpha calculation
        risk_free_rate: Annual risk-free rate for Sharpe/Alpha
        periods_per_year: Trading periods per year (252 daily, 365 crypto)
    
    Returns:
        Comprehensive results dictionary with metrics
    """
    if data.empty:
        return {"start_portfolio_value": cash, "end_portfolio_value": cash, "pnl": 0.0}

    # Validate and clean data
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing_cols = [col for col in required_columns if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("Data index must be a DatetimeIndex")
    
    data = data[required_columns].copy()
    data = data.dropna(subset=required_columns)
    data = data.sort_index()
    
    for col in required_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    data = data.dropna()
    
    if data.empty:
        return {"start_portfolio_value": cash, "end_portfolio_value": cash, "pnl": 0.0}
    
    data_count = len(data)
    warnings = []
    
    if data_count < 50:
        warnings.append(f"Limited data: Only {data_count} bars available.")
    elif data_count < 100:
        warnings.append(f"Moderate data: {data_count} bars available.")
    
    date_range = {
        "start": str(data.index.min()),
        "end": str(data.index.max()),
        "bars_count": data_count
    }

    try:
        cerebro = bt.Cerebro()
        
        # Add strategy
        if ticker:
            class StrategyWithTicker(strategy_class):
                def __init__(self):
                    super().__init__()
                    self.ticker = ticker
            cerebro.addstrategy(StrategyWithTicker)
        else:
            cerebro.addstrategy(strategy_class)
        
        # Add analyzers for comprehensive metrics
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=risk_free_rate/periods_per_year)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        
        # Track equity curve using an observer
        equity_values = []
        equity_dates = []
        
        class EquityObserver(bt.Observer):
            lines = ('equity',)
            plotinfo = dict(plot=False)
            
            def next(self):
                equity_values.append(self._owner.broker.getvalue())
                equity_dates.append(self._owner.data.datetime.datetime(0))
        
        cerebro.addobserver(EquityObserver)
        
        # Add data feed
        data_feed = bt.feeds.PandasData(dataname=data)
        cerebro.adddata(data_feed)
        
        # Add benchmark if provided
        benchmark_returns = None
        if benchmark_data is not None:
            benchmark_feed = bt.feeds.PandasData(dataname=benchmark_data)
            cerebro.adddata(benchmark_feed, name="benchmark")
        
        # Configure broker
        cerebro.broker.setcash(cash)
        
        # Configure cost models
        if slippage_model == "dynamic":
            cerebro.broker.set_slippage(DynamicSlippage())
        elif slippage_model == "market_impact":
            cerebro.broker.set_slippage(MarketImpactSlippage())
        
        # Use enhanced commission model
        comminfo = EliteCommission(
            commission=commission,
            per_share=0.0,
            min_commission=1.0
        )
        cerebro.broker.setcommission(commission=commission)
        
        # Run backtest
        start_portfolio_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_portfolio_value = cerebro.broker.getvalue()
        
        # Extract analyzer results
        strat_result = results[0]
        trade_analyzer = strat_result.analyzers.trades.get_analysis()
        
        # Get Sharpe Ratio (if available)
        sharpe_ratio = 0.0
        try:
            sharpe_analyzer = strat_result.analyzers.sharpe.get_analysis()
            if 'sharperatio' in sharpe_analyzer:
                sharpe_ratio = sharpe_analyzer['sharperatio']
        except:
            pass
        
        # Get Drawdown (if available)
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        try:
            drawdown_analyzer = strat_result.analyzers.drawdown.get_analysis()
            if 'max' in drawdown_analyzer:
                max_drawdown = drawdown_analyzer['max']['drawdown']
                max_drawdown_pct = drawdown_analyzer['max']['drawdown']
        except:
            pass
        
        # Build equity curve from observer
        if equity_values and equity_dates:
            equity_curve = pd.Series(equity_values, index=pd.DatetimeIndex(equity_dates))
        else:
            # Fallback: simple approximation
            equity_curve = pd.Series(
                [start_portfolio_value] * len(data),
                index=data.index
            )
            equity_curve.iloc[-1] = end_portfolio_value
        
        # Extract trades
        trades = []
        if hasattr(trade_analyzer, 'total') and trade_analyzer.total.total > 0:
            # Extract trade information
            total_trades = trade_analyzer.total.total
            won_trades = trade_analyzer.won.total if hasattr(trade_analyzer, 'won') else 0
            lost_trades = trade_analyzer.lost.total if hasattr(trade_analyzer, 'lost') else 0
            
            # Calculate metrics
            win_rate = won_trades / total_trades if total_trades > 0 else 0.0
            avg_win = trade_analyzer.won.pnl.average if hasattr(trade_analyzer, 'won') else 0.0
            avg_loss = abs(trade_analyzer.lost.pnl.average) if hasattr(trade_analyzer, 'lost') else 0.0
            
            total_profit = trade_analyzer.won.pnl.total if hasattr(trade_analyzer, 'won') else 0.0
            total_loss = abs(trade_analyzer.lost.pnl.total) if hasattr(trade_analyzer, 'lost') else 0.0
            profit_factor = total_profit / total_loss if total_loss > 0 else 0.0
            
            trades = [{
                'total': total_trades,
                'won': won_trades,
                'lost': lost_trades,
            }]
        
        # Calculate comprehensive metrics
        benchmark_returns_series = None
        if benchmark_data is not None and 'Close' in benchmark_data.columns:
            benchmark_returns_series = benchmark_data['Close'].pct_change().dropna()
        
        # Use analyzer results where available, otherwise calculate
        if trades and len(trades) > 0:
            trade_info = trades[0]
            win_rate = trade_info.get('won', 0) / trade_info.get('total', 1) if trade_info.get('total', 0) > 0 else 0.0
            trades_count = trade_info.get('total', 0)
        else:
            win_rate = 0.0
            trades_count = 0
        
        # Calculate metrics (using analyzer results where better)
        metrics = calculate_comprehensive_metrics(
            equity_curve=equity_curve,
            trades=None,  # Use analyzer results instead
            benchmark_returns=benchmark_returns_series,
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
            initial_capital=cash,
        )
        
        # Override with analyzer results where available (these are more accurate)
        if sharpe_ratio != 0:
            metrics.sharpe_ratio = sharpe_ratio
        if max_drawdown_pct > 0:
            metrics.max_drawdown_pct = max_drawdown_pct
            metrics.max_drawdown = max_drawdown
        
        # Use trade analyzer results for win rate and profit factor
        if trades and len(trades) > 0:
            trade_info = trades[0]
            if trade_info.get('total', 0) > 0:
                metrics.win_rate = win_rate
                metrics.trades_count = trade_info.get('total', 0)
                metrics.profit_factor = profit_factor
                metrics.avg_win = avg_win
                metrics.avg_loss = avg_loss
        
        # Calculate percentage return
        pnl_pct = ((end_portfolio_value - start_portfolio_value) / start_portfolio_value) * 100 if start_portfolio_value > 0 else 0.0
        
        result = {
            "start_portfolio_value": start_portfolio_value,
            "end_portfolio_value": end_portfolio_value,
            "pnl": end_portfolio_value - start_portfolio_value,
            "pnl_percentage": round(pnl_pct, 2),
            "data_info": date_range,
            "warnings": warnings if warnings else None,
            # Advanced metrics
            "metrics": {
                "sharpe_ratio": round(metrics.sharpe_ratio, 3),
                "max_drawdown": round(metrics.max_drawdown, 2),
                "max_drawdown_pct": round(metrics.max_drawdown_pct, 2),
                "calmar_ratio": round(metrics.calmar_ratio, 3),
                "alpha": round(metrics.alpha, 3) if metrics.alpha is not None else None,
                "volatility": round(metrics.volatility, 2),
                "win_rate": round(metrics.win_rate * 100, 2),
                "profit_factor": round(metrics.profit_factor, 2),
                "position_turnover": round(metrics.position_turnover, 2),
                "trades_count": metrics.trades_count,
            },
            "equity_curve": {str(k): float(v) for k, v in equity_curve.to_dict().items()} if len(equity_curve) > 0 else {},
        }
        
        return result
    except Exception as e:
        error_msg = f"Backtest execution failed: {str(e)}"
        if data_count < 50:
            error_msg += f" (Limited data: {data_count} bars)"
        raise RuntimeError(error_msg) from e

