"""
Advanced Position Sizing Algorithms

Implements optimal position sizing methods as specified in elite trading research:
- Optimal f (Ralph Vince)
- Kelly Criterion
- Fixed Fractional
- Risk-based sizing (based on stop loss distance)
"""
import numpy as np
from typing import List, Optional
import pandas as pd


def optimal_f(returns: List[float]) -> float:
    """
    Calculate Optimal f (Ralph Vince) - the fraction of capital to risk per trade.
    
    Optimal f maximizes the geometric mean of returns. It's the fraction that
    would have produced maximum profit over the historical sequence.
    
    Args:
        returns: List of trade returns (as fractions, e.g., 0.05 for 5%)
    
    Returns:
        Optimal f value (0.0 to 1.0)
    """
    if not returns or len(returns) == 0:
        return 0.0
    
    returns = np.array(returns)
    
    # Remove zero returns
    returns = returns[returns != 0]
    
    if len(returns) == 0:
        return 0.0
    
    # Optimal f is found by maximizing the geometric mean
    # We'll use a numerical search
    f_values = np.linspace(0.01, 0.99, 100)
    best_f = 0.01
    best_gmean = -np.inf
    
    for f in f_values:
        # Calculate terminal wealth for each f
        hpr = 1 + f * returns  # Holding Period Return
        gmean = np.prod(hpr) ** (1.0 / len(hpr))
        
        if gmean > best_gmean and gmean > 0:
            best_gmean = gmean
            best_f = f
    
    return float(best_f)


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate Kelly Criterion - optimal bet size for maximizing long-term growth.
    
    Kelly% = (Win Rate * Avg Win - Loss Rate * Avg Loss) / Avg Win
    
    Args:
        win_rate: Probability of winning (0.0 to 1.0)
        avg_win: Average winning trade return (as fraction)
        avg_loss: Average losing trade return (as fraction, positive value)
    
    Returns:
        Kelly fraction (0.0 to 1.0, can exceed 1.0 for very favorable bets)
    """
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    
    loss_rate = 1.0 - win_rate
    
    # Kelly formula
    kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
    
    # Cap at 1.0 (100%) for safety - full Kelly is often too aggressive
    return max(0.0, min(1.0, kelly))


def fractional_kelly(kelly_fraction: float, safety_factor: float = 0.5) -> float:
    """
    Calculate fractional Kelly for risk management.
    
    Full Kelly is often too aggressive. Fractional Kelly (typically 0.25-0.5)
    provides better risk-adjusted returns.
    
    Args:
        kelly_fraction: Full Kelly fraction
        safety_factor: Fraction to use (0.5 = half Kelly)
    
    Returns:
        Fractional Kelly
    """
    return kelly_fraction * safety_factor


def calculate_position_size(
    account_balance: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
    method: str = "fixed_risk"
) -> int:
    """
    Calculate position size based on risk parameters.
    
    Args:
        account_balance: Current account balance
        risk_per_trade: Risk amount per trade (dollars or fraction)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        method: Sizing method ('fixed_risk', 'fixed_fraction', 'optimal_f')
    
    Returns:
        Number of shares/units to trade
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0
    
    # Calculate risk per share
    risk_per_share = abs(entry_price - stop_loss_price)
    
    if risk_per_share == 0:
        return 0
    
    if method == "fixed_risk":
        # Risk fixed dollar amount
        if risk_per_trade <= 0:
            return 0
        position_size = risk_per_trade / risk_per_share
    elif method == "fixed_fraction":
        # Risk fixed percentage of account
        risk_amount = account_balance * risk_per_trade
        position_size = risk_amount / risk_per_share
    else:
        # Default to fixed risk
        position_size = risk_per_trade / risk_per_share
    
    return int(max(0, position_size))


def calculate_risk_based_size(
    account_balance: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
    max_position_pct: float = 0.25
) -> int:
    """
    Calculate position size with risk-based constraints.
    
    Ensures position doesn't exceed maximum allocation percentage.
    
    Args:
        account_balance: Current account balance
        risk_pct: Risk percentage per trade (e.g., 0.02 for 2%)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        max_position_pct: Maximum position size as % of account
    
    Returns:
        Number of shares/units
    """
    # Calculate risk-based size
    risk_amount = account_balance * risk_pct
    risk_per_share = abs(entry_price - stop_loss_price)
    
    if risk_per_share == 0:
        return 0
    
    risk_based_size = risk_amount / risk_per_share
    
    # Apply maximum position constraint
    max_position_value = account_balance * max_position_pct
    max_shares_by_value = max_position_value / entry_price if entry_price > 0 else 0
    
    # Use the smaller of the two
    final_size = min(risk_based_size, max_shares_by_value)
    
    return int(max(0, final_size))

