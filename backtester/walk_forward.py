"""
Walk-Forward Analysis for Strategy Validation

Implements rigorous validation protocol to prevent overfitting:
- Out-of-sample testing
- Rolling window optimization
- Multiple market regime validation
"""
import pandas as pd
import numpy as np
from typing import Type, Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import backtrader as bt

from backtester.engine import run_backtest
from backtester.metrics import StrategyMetrics, calculate_comprehensive_metrics


def walk_forward_analysis(
    strategy_class: Type[bt.Strategy],
    data: pd.DataFrame,
    train_window: int = 252,  # Training window in periods
    test_window: int = 63,     # Testing window in periods
    step_size: int = 21,        # Step size for rolling window
    cash: float = 10000.0,
    commission: float = 0.001,
    ticker: Optional[str] = None,
    optimize_params: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Perform walk-forward analysis to validate strategy robustness.
    
    The walk-forward process:
    1. Train/optimize on training window
    2. Test on subsequent out-of-sample period
    3. Roll forward and repeat
    
    Args:
        strategy_class: Strategy class to test
        data: Full historical dataset
        train_window: Training period length (periods)
        test_window: Testing period length (periods)
        step_size: How much to roll forward each iteration
        cash: Initial capital
        commission: Commission rate
        ticker: Optional ticker symbol
        optimize_params: Optional function to optimize parameters on training data
    
    Returns:
        Dictionary with walk-forward results and statistics
    """
    if len(data) < train_window + test_window:
        raise ValueError(f"Insufficient data: need at least {train_window + test_window} periods")
    
    results = []
    total_periods = len(data)
    
    # Walk forward through the data
    start_idx = 0
    iteration = 0
    
    while start_idx + train_window + test_window <= total_periods:
        iteration += 1
        
        # Define windows
        train_start = start_idx
        train_end = start_idx + train_window
        test_start = train_end
        test_end = test_start + test_window
        
        train_data = data.iloc[train_start:train_end]
        test_data = data.iloc[test_start:test_end]
        
        # Optimize parameters on training data (if function provided)
        best_params = None
        if optimize_params:
            best_params = optimize_params(strategy_class, train_data, cash, commission, ticker)
        
        # Test on out-of-sample data
        try:
            if best_params:
                # Create strategy with optimized parameters
                class OptimizedStrategy(strategy_class):
                    params = best_params
                test_strategy = OptimizedStrategy
            else:
                test_strategy = strategy_class
            
            result = run_backtest(
                strategy_class=test_strategy,
                data=test_data,
                cash=cash,
                commission=commission,
                ticker=ticker,
            )
            
            results.append({
                'iteration': iteration,
                'train_start': str(train_data.index[0]),
                'train_end': str(train_data.index[-1]),
                'test_start': str(test_data.index[0]),
                'test_end': str(test_data.index[-1]),
                'pnl': result.get('pnl', 0),
                'pnl_percentage': result.get('pnl_percentage', 0),
                'start_value': result.get('start_portfolio_value', cash),
                'end_value': result.get('end_portfolio_value', cash),
                'params': best_params,
            })
        except Exception as e:
            print(f"Walk-forward iteration {iteration} failed: {e}")
            continue
        
        # Roll forward
        start_idx += step_size
    
    if not results:
        return {"error": "No successful walk-forward iterations"}
    
    # Aggregate statistics
    pnls = [r['pnl'] for r in results]
    returns = [r['pnl_percentage'] for r in results]
    
    # Calculate consistency metrics
    positive_periods = sum(1 for r in returns if r > 0)
    consistency = positive_periods / len(results) if results else 0.0
    
    # Calculate equity curve
    cumulative_equity = [cash]
    for r in results:
        cumulative_equity.append(cumulative_equity[-1] + r['pnl'])
    
    equity_series = pd.Series(cumulative_equity[1:])
    
    # Calculate overall metrics
    overall_metrics = calculate_comprehensive_metrics(
        equity_curve=equity_series,
        trades=None,
        benchmark_returns=None,
        risk_free_rate=0.0,
        periods_per_year=252,
        initial_capital=cash,
    )
    
    return {
        "iterations": len(results),
        "results": results,
        "summary": {
            "total_pnl": sum(pnls),
            "total_return_pct": ((cumulative_equity[-1] - cash) / cash) * 100,
            "avg_period_return": np.mean(returns),
            "std_period_return": np.std(returns),
            "best_period_return": max(returns),
            "worst_period_return": min(returns),
            "consistency": consistency * 100,
            "positive_periods": positive_periods,
            "total_periods": len(results),
        },
        "metrics": {
            "sharpe_ratio": overall_metrics.sharpe_ratio,
            "max_drawdown_pct": overall_metrics.max_drawdown_pct,
            "calmar_ratio": overall_metrics.calmar_ratio,
        },
    }

