"""
Advanced Risk and Performance Metrics for Trading Strategies

Implements comprehensive evaluation metrics as specified in elite trading research:
- Sharpe Ratio (risk-adjusted return)
- Maximum Drawdown (capital preservation)
- Calmar Ratio (return/drawdown efficiency)
- Alpha (excess return vs benchmark)
- Position Turnover Rate
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class StrategyMetrics:
    """Comprehensive metrics for strategy evaluation"""
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    calmar_ratio: float
    alpha: Optional[float]
    total_return: float
    total_return_pct: float
    volatility: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    position_turnover: float
    trades_count: int
    avg_trade_duration: float


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate period returns from equity curve.
    
    Args:
        equity_curve: Series of portfolio values over time
    
    Returns:
        Series of period returns
    """
    if len(equity_curve) == 0:
        return pd.Series(dtype=float)
    return equity_curve.pct_change().dropna()


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate annualized Sharpe Ratio.
    
    Sharpe Ratio = (Mean Return - Risk-Free Rate) / Std Deviation
    
    Args:
        returns: Series of period returns
        risk_free_rate: Annual risk-free rate (default 0.0)
        periods_per_year: Trading periods per year (252 for daily, 365 for crypto)
    
    Returns:
        Annualized Sharpe Ratio
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_returns = returns - (risk_free_rate / periods_per_year)
    sharpe = (excess_returns.mean() * np.sqrt(periods_per_year)) / returns.std()
    
    return float(sharpe) if not np.isnan(sharpe) else 0.0


def calculate_max_drawdown(equity_curve: pd.Series) -> tuple[float, float]:
    """
    Calculate Maximum Drawdown (MDD) in absolute and percentage terms.
    
    MDD = Max(Peak - Trough) / Peak
    
    Args:
        equity_curve: Series of portfolio values over time
    
    Returns:
        (absolute_drawdown, percentage_drawdown)
    """
    if len(equity_curve) == 0:
        return 0.0, 0.0
    
    # Calculate running maximum (peak)
    running_max = equity_curve.expanding().max()
    
    # Calculate drawdown from peak
    drawdown = running_max - equity_curve
    
    # Maximum drawdown
    max_dd = drawdown.max()
    max_dd_pct = (max_dd / running_max.max()) * 100 if running_max.max() > 0 else 0.0
    
    return float(max_dd), float(max_dd_pct)


def calculate_calmar_ratio(
    annual_return: float,
    max_drawdown_pct: float
) -> float:
    """
    Calculate Calmar Ratio: Annual Return / Maximum Drawdown
    
    Higher is better - measures return efficiency relative to worst loss.
    
    Args:
        annual_return: Annualized return percentage
        max_drawdown_pct: Maximum drawdown percentage
    
    Returns:
        Calmar Ratio
    """
    if max_drawdown_pct == 0:
        return 0.0 if annual_return == 0 else float('inf')
    
    return annual_return / abs(max_drawdown_pct)


def calculate_alpha(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Alpha (excess return vs benchmark) using CAPM.
    
    Alpha = (Strategy Return - Risk-Free) - Beta * (Benchmark Return - Risk-Free)
    
    Args:
        strategy_returns: Strategy period returns
        benchmark_returns: Benchmark period returns (e.g., S&P 500)
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year
    
    Returns:
        Annualized Alpha
    """
    if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
        return 0.0
    
    # Align returns
    aligned = pd.DataFrame({
        'strategy': strategy_returns,
        'benchmark': benchmark_returns
    }).dropna()
    
    if len(aligned) == 0:
        return 0.0
    
    strategy = aligned['strategy']
    benchmark = aligned['benchmark']
    
    # Calculate Beta (covariance / variance of benchmark)
    if benchmark.std() == 0:
        return 0.0
    
    beta = strategy.cov(benchmark) / benchmark.var()
    
    # Annualize returns
    strategy_annual = strategy.mean() * periods_per_year
    benchmark_annual = benchmark.mean() * periods_per_year
    
    # Calculate Alpha
    alpha = (strategy_annual - risk_free_rate) - beta * (benchmark_annual - risk_free_rate)
    
    return float(alpha * 100)  # Return as percentage


def calculate_trade_metrics(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate trade-level metrics from list of trades.
    
    Args:
        trades: List of trade dictionaries with keys: 'pnl', 'duration', etc.
    
    Returns:
        Dictionary of trade metrics
    """
    if not trades:
        return {
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'trades_count': 0,
            'avg_trade_duration': 0.0,
        }
    
    pnls = [t.get('pnl', 0.0) for t in trades if 'pnl' in t]
    durations = [t.get('duration', 0.0) for t in trades if 'duration' in t]
    
    if not pnls:
        return {
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'trades_count': len(trades),
            'avg_trade_duration': float(np.mean(durations)) if durations else 0.0,
        }
    
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(abs(np.mean(losses))) if losses else 0.0
    
    total_profit = sum(wins) if wins else 0.0
    total_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = total_profit / total_loss if total_loss > 0 else (float('inf') if total_profit > 0 else 0.0)
    
    return {
        'win_rate': win_rate,
        'profit_factor': profit_factor if profit_factor != float('inf') else 999.0,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'trades_count': len(trades),
        'avg_trade_duration': float(np.mean(durations)) if durations else 0.0,
    }


def calculate_position_turnover(
    equity_curve: pd.Series,
    total_trades: int,
    periods_per_year: int = 252
) -> float:
    """
    Calculate position turnover rate (trades per year).
    
    Args:
        equity_curve: Series of portfolio values
        total_trades: Total number of trades executed
        periods_per_year: Trading periods per year
    
    Returns:
        Annualized turnover rate
    """
    if len(equity_curve) == 0:
        return 0.0
    
    years = len(equity_curve) / periods_per_year
    return total_trades / years if years > 0 else 0.0


def calculate_comprehensive_metrics(
    equity_curve: pd.Series,
    trades: Optional[List[Dict[str, Any]]] = None,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    initial_capital: Optional[float] = None
) -> StrategyMetrics:
    """
    Calculate comprehensive strategy metrics.
    
    Args:
        equity_curve: Series of portfolio values over time
        trades: Optional list of trade dictionaries
        benchmark_returns: Optional benchmark returns for Alpha calculation
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year
        initial_capital: Initial capital (for percentage calculations)
    
    Returns:
        StrategyMetrics object with all calculated metrics
    """
    if len(equity_curve) == 0:
        return StrategyMetrics(
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            calmar_ratio=0.0,
            alpha=None,
            total_return=0.0,
            total_return_pct=0.0,
            volatility=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            position_turnover=0.0,
            trades_count=0,
            avg_trade_duration=0.0,
        )
    
    # Calculate returns
    returns = calculate_returns(equity_curve)
    
    # Basic metrics
    initial_value = equity_curve.iloc[0] if initial_capital is None else initial_capital
    final_value = equity_curve.iloc[-1]
    total_return = final_value - initial_value
    total_return_pct = (total_return / initial_value) * 100 if initial_value > 0 else 0.0
    
    # Annualized return
    years = len(equity_curve) / periods_per_year
    annual_return = ((final_value / initial_value) ** (1 / years) - 1) * 100 if years > 0 and initial_value > 0 else 0.0
    
    # Risk metrics
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)
    max_dd, max_dd_pct = calculate_max_drawdown(equity_curve)
    calmar = calculate_calmar_ratio(annual_return, max_dd_pct)
    
    # Volatility (annualized)
    volatility = returns.std() * np.sqrt(periods_per_year) * 100 if len(returns) > 0 else 0.0
    
    # Trade metrics
    trade_metrics = calculate_trade_metrics(trades or [])
    
    # Position turnover
    turnover = calculate_position_turnover(
        equity_curve,
        trade_metrics['trades_count'],
        periods_per_year
    )
    
    # Alpha (if benchmark provided)
    alpha = None
    if benchmark_returns is not None:
        alpha = calculate_alpha(returns, benchmark_returns, risk_free_rate, periods_per_year)
    
    return StrategyMetrics(
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        calmar_ratio=calmar,
        alpha=alpha,
        total_return=total_return,
        total_return_pct=total_return_pct,
        volatility=volatility,
        win_rate=trade_metrics['win_rate'],
        profit_factor=trade_metrics['profit_factor'],
        avg_win=trade_metrics['avg_win'],
        avg_loss=trade_metrics['avg_loss'],
        position_turnover=turnover,
        trades_count=trade_metrics['trades_count'],
        avg_trade_duration=trade_metrics['avg_trade_duration'],
    )

