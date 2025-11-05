"""
Advanced Strategy Base Class with Integrated Risk Management

Provides foundation for elite strategies with:
- Maximum Drawdown constraints
- Position sizing based on risk
- Volatility-based position adjustment
- Multi-timeframe support
"""
import backtrader as bt
from typing import Optional
import numpy as np

from backtester.position_sizing import calculate_risk_based_size


class AdvancedStrategyBase(bt.Strategy):
    """
    Base class for advanced strategies with integrated risk management.
    
    Features:
    - Maximum Drawdown protection
    - Dynamic position sizing
    - Volatility-adjusted position sizing
    - Risk-based stop losses
    """
    
    params = (
        # Risk Management
        ('max_drawdown_pct', 20.0),      # Maximum drawdown % before pausing
        ('risk_per_trade', 0.02),        # Risk 2% per trade
        ('max_position_pct', 0.25),      # Maximum 25% of capital per position
        ('use_volatility_adjustment', True),  # Adjust size based on volatility
        ('atr_period', 14),               # ATR period for volatility
        ('atr_multiplier', 2.0),          # ATR multiplier for stops
    )
    
    def __init__(self):
        # Track equity curve for drawdown monitoring
        self.equity_curve = []
        self.peak_equity = self.broker.getvalue()
        self.max_drawdown = 0.0
        self.paused = False  # Pause trading if drawdown limit hit
        
        # Volatility indicators
        if self.params.use_volatility_adjustment:
            self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
            self.atr_ma = bt.indicators.SimpleMovingAverage(self.atr, period=20)
        
        # Volume for position sizing
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=20
        )
        
        # Track trades
        self.trade_count = 0
        self.win_count = 0
    
    def next(self):
        """Update equity tracking and check drawdown"""
        current_value = self.broker.getvalue()
        self.equity_curve.append(current_value)
        
        # Update peak equity
        if current_value > self.peak_equity:
            self.peak_equity = current_value
        
        # Calculate current drawdown
        current_drawdown = ((self.peak_equity - current_value) / self.peak_equity) * 100
        
        # Update max drawdown
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Pause trading if drawdown limit exceeded
        if current_drawdown >= self.params.max_drawdown_pct:
            self.paused = True
            if self.position:
                # Close existing positions
                self.close()
        else:
            self.paused = False
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> int:
        """
        Calculate position size using risk-based sizing.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
        
        Returns:
            Number of shares/units
        """
        if self.paused:
            return 0
        
        account_balance = self.broker.getvalue()
        
        # Base position size from risk
        size = calculate_risk_based_size(
            account_balance=account_balance,
            risk_pct=self.params.risk_per_trade,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            max_position_pct=self.params.max_position_pct,
        )
        
        # Volatility adjustment: reduce size in high volatility
        if self.params.use_volatility_adjustment and self.atr_ma[0] > 0:
            volatility_ratio = self.atr[0] / self.atr_ma[0]
            # Reduce size if volatility is above average
            if volatility_ratio > 1.5:
                size = int(size * 0.5)  # Reduce by 50% in high volatility
            elif volatility_ratio > 1.2:
                size = int(size * 0.75)  # Reduce by 25%
        
        return max(0, size)
    
    def calculate_stop_loss(self, entry_price: float, direction: str = "long") -> float:
        """
        Calculate stop loss based on ATR.
        
        Args:
            entry_price: Entry price
            direction: "long" or "short"
        
        Returns:
            Stop loss price
        """
        if not self.params.use_volatility_adjustment:
            # Default: 2% stop
            stop_pct = 0.02
            if direction == "long":
                return entry_price * (1 - stop_pct)
            else:
                return entry_price * (1 + stop_pct)
        
        # ATR-based stop
        atr_value = self.atr[0]
        
        if direction == "long":
            stop_loss = entry_price - (atr_value * self.params.atr_multiplier)
        else:
            stop_loss = entry_price + (atr_value * self.params.atr_multiplier)
        
        return stop_loss
    
    def notify_trade(self, trade):
        """Track trade statistics"""
        if trade.isclosed:
            self.trade_count += 1
            if trade.pnl > 0:
                self.win_count += 1
    
    def get_win_rate(self) -> float:
        """Get current win rate"""
        if self.trade_count == 0:
            return 0.0
        return self.win_count / self.trade_count
    
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

