"""
Advanced Cost Modeling for High-Fidelity Backtesting

Implements dynamic slippage and market impact modeling as required for elite strategies.
Costs are not fixed percentages but dynamic functions tied to:
- Trade size relative to market depth
- Current market liquidity
- Volatility regime

Note: These classes use backtrader's slippage interface. For simpler slippage,
use cerebro.broker.set_slippage_fixed() or cerebro.broker.set_slippage_perc().
"""
import backtrader as bt
from typing import Optional
import numpy as np

# Note: backtrader may not have Slippage class in all versions
# We'll create a base class that works with backtrader's slippage interface
class _SlippageBase:
    """Base class for slippage implementation"""
    params = ()
    def __init__(self):
        pass
    def __call__(self, order, price, size):
        return price, size

# Try to use backtrader's Slippage if available, otherwise use our base
try:
    _SlippageBase = bt.Slippage
except AttributeError:
    pass  # Use our _SlippageBase above


class DynamicSlippage(_SlippageBase):
    """
    Dynamic slippage model that accounts for:
    - Trade size relative to average volume
    - Current volatility regime
    - Market impact (larger orders = higher slippage)
    """
    
    params = (
        ('volume_impact_factor', 0.1),  # Impact per 1% of volume
        ('volatility_factor', 0.5),    # Additional impact in high volatility
        ('base_slippage', 0.0005),      # Base slippage (0.05%)
        ('max_slippage', 0.01),         # Maximum slippage cap (1%)
    )
    
    def __init__(self):
        super().__init__()
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )
        # Volatility proxy using ATR
        self.atr = bt.indicators.ATR(self.data, period=14)
        self.atr_ma = bt.indicators.SimpleMovingAverage(self.atr, period=20)
    
    def _get_slippage(self, order):
        """Calculate dynamic slippage based on order size and market conditions"""
        if not order.size:
            return 0.0
        
        # Base slippage
        slippage = self.params.base_slippage
        
        # Volume impact: larger relative orders = more slippage
        if self.volume_ma[0] > 0:
            volume_pct = abs(order.size) / self.volume_ma[0]
            volume_impact = volume_pct * self.params.volume_impact_factor
            slippage += min(volume_impact, 0.005)  # Cap at 0.5%
        
        # Volatility impact: higher volatility = more slippage
        if self.atr_ma[0] > 0:
            volatility_ratio = self.atr[0] / self.atr_ma[0]
            volatility_impact = (volatility_ratio - 1.0) * self.params.volatility_factor * self.params.base_slippage
            slippage += max(0.0, volatility_impact)
        
        # Cap at maximum
        slippage = min(slippage, self.params.max_slippage)
        
        return slippage
    
    def __call__(self, order, price, size):
        """Execute order with dynamic slippage"""
        slippage_pct = self._get_slippage(order)
        
        # Apply slippage in direction of trade
        if size > 0:  # Buy order
            executed_price = price * (1 + slippage_pct)
        else:  # Sell order
            executed_price = price * (1 - slippage_pct)
        
        return executed_price, size


class MarketImpactSlippage(_SlippageBase):
    """
    Market impact model based on square-root law.
    Larger orders have non-linear impact: Impact ∝ √(Size)
    """
    
    params = (
        ('impact_factor', 0.01),        # Base impact factor
        ('volume_lookback', 20),        # Period for average volume
        ('base_slippage', 0.0005),      # Base slippage
    )
    
    def __init__(self):
        super().__init__()
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.volume_lookback
        )
    
    def _calculate_impact(self, order_size, avg_volume):
        """Calculate market impact using square-root law"""
        if avg_volume <= 0:
            return self.params.base_slippage
        
        # Normalize order size to volume
        relative_size = abs(order_size) / avg_volume
        
        # Square-root law: impact scales with square root of size
        impact = self.params.impact_factor * np.sqrt(relative_size)
        
        # Add base slippage
        total_slippage = self.params.base_slippage + impact
        
        return min(total_slippage, 0.02)  # Cap at 2%
    
    def __call__(self, order, price, size):
        """Execute order with market impact"""
        if self.volume_ma[0] > 0:
            impact = self._calculate_impact(size, self.volume_ma[0])
        else:
            impact = self.params.base_slippage
        
        # Apply impact
        if size > 0:  # Buy
            executed_price = price * (1 + impact)
        else:  # Sell
            executed_price = price * (1 - impact)
        
        return executed_price, size


class EliteCommission(bt.CommInfoBase):
    """
    Enhanced commission model with:
    - Per-share fees (common in professional trading)
    - Minimum commission per trade
    - Percentage-based commission
    """
    
    params = (
        ('commission', 0.001),      # Percentage commission (0.1%)
        ('mult', 1.0),              # Multiplier
        ('margin', None),            # Margin requirement
        ('commtype', None),          # Commission type
        ('stocklike', True),         # Stock-like instrument
        ('percabs', False),         # Percentage absolute
        ('per_share', 0.0),         # Per-share commission
        ('min_commission', 1.0),    # Minimum commission per trade
    )
    
    def _getcommission(self, size, price, pseudoexec):
        """Calculate commission with per-share and minimum"""
        # Base percentage commission
        comm = abs(size) * price * self.params.commission
        
        # Add per-share commission
        if self.params.per_share > 0:
            comm += abs(size) * self.params.per_share
        
        # Apply minimum
        if comm < self.params.min_commission:
            comm = self.params.min_commission
        
        return comm

