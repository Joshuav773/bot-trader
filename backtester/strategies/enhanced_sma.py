"""
Enhanced SMA Crossover Strategy with Advanced Risk Management

Implements elite trading principles:
- Risk-based position sizing
- Maximum drawdown protection
- Volatility-adjusted entries
- ATR-based stop losses
"""
import backtrader as bt
from backtester.strategies.base_strategy import AdvancedStrategyBase


class EnhancedSmaCrossover(AdvancedStrategyBase):
    """
    Enhanced SMA Crossover with integrated risk management.
    
    Uses the AdvancedStrategyBase for:
    - Drawdown protection
    - Risk-based position sizing
    - Volatility adjustment
    """
    
    params = (
        # Strategy parameters
        ("fast_length", 10),
        ("slow_length", 50),
        # Risk management (inherited from base)
        ("max_drawdown_pct", 20.0),
        ("risk_per_trade", 0.02),
        ("max_position_pct", 0.25),
        ("use_volatility_adjustment", True),
        ("atr_period", 14),
        ("atr_multiplier", 2.0),
    )
    
    def __init__(self):
        super().__init__()
        
        # Moving averages
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_length
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_length
        )
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # Additional filters
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        
        # Track entry price for stop loss
        self.entry_price = None
        self.stop_loss = None
    
    def next(self):
        """Main strategy logic"""
        # Call parent to update drawdown tracking
        super().next()
        
        # Don't trade if paused due to drawdown
        if self.paused:
            return
        
        # Exit if stop loss hit
        if self.position:
            if self.stop_loss:
                if self.data.close[0] <= self.stop_loss:
                    self.log(f"STOP LOSS HIT: {self.data.close[0]:.2f} <= {self.stop_loss:.2f}")
                    self.close()
                    self.entry_price = None
                    self.stop_loss = None
                    return
            # Exit on bearish crossover
            if self.crossover < 0:
                self.log(f"SELL SIGNAL: Crossover bearish at {self.data.close[0]:.2f}")
                self.close()
                self.entry_price = None
                self.stop_loss = None
        
        # Entry logic
        if not self.position:
            # Bullish crossover signal
            if self.crossover > 0:
                # Additional filter: RSI not overbought
                if self.rsi[0] < 70:
                    entry_price = self.data.close[0]
                    stop_loss = self.calculate_stop_loss(entry_price, "long")
                    
                    # Calculate position size
                    size = self.calculate_position_size(entry_price, stop_loss)
                    
                    if size > 0:
                        self.log(f"BUY SIGNAL: {size} shares at {entry_price:.2f}, stop: {stop_loss:.2f}")
                        self.buy(size=size)
                        self.entry_price = entry_price
                        self.stop_loss = stop_loss
    
    def log(self, txt, dt=None):
        """Logger"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

