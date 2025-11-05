import backtrader as bt


class BollingerBandsStrategy(bt.Strategy):
    """
    Mean-Reversion strategy using Bollinger Bands.
    
    Strategy Logic:
    - Buy when price touches or crosses below the lower band (oversold)
    - Sell when price touches or crosses above the upper band (overbought)
    - Price should revert to the middle band (SMA)
    """
    
    params = (
        ("period", 20),  # Period for Bollinger Bands SMA
        ("devfactor", 2.0),  # Number of standard deviations for bands
        ("size", 0.95),  # Percentage of cash to use per trade
    )
    
    def __init__(self):
        # Bollinger Bands indicator
        self.bbands = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor
        )
        
        # Keep track of pending orders
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
    def log(self, txt, dt=None):
        """Logger function for the strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"BUY EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log(
                    f"SELL EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
        
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")
    
    def next(self):
        if self.order:
            return
        
        # Get current price and bands
        current_price = self.data.close[0]
        lower_band = self.bbands.lines.bot[0]
        upper_band = self.bbands.lines.top[0]
        middle_band = self.bbands.lines.mid[0]
        
        # Mean reversion logic
        if not self.position:  # Not in the market
            # Buy signal: price touches or goes below lower band (oversold)
            if current_price <= lower_band:
                # Calculate position size (percentage of cash)
                size = int((self.broker.getcash() * self.params.size) / current_price)
                if size > 0:
                    self.log(f"BUY CREATE, Price: {current_price:.2f}, Lower Band: {lower_band:.2f}")
                    self.order = self.buy(size=size)
        else:  # In the market
            # Sell signal: price touches or goes above upper band (overbought)
            # OR price reaches middle band (take profit on reversion)
            if current_price >= upper_band:
                self.log(f"SELL CREATE, Price: {current_price:.2f}, Upper Band: {upper_band:.2f}")
                self.order = self.close()
            elif current_price >= middle_band and self.buyprice:
                # Optional: take profit when price reverts to middle
                # This is less aggressive than waiting for upper band
                profit_pct = ((current_price - self.buyprice) / self.buyprice) * 100
                if profit_pct > 2.0:  # Take profit if we're up 2%+
                    self.log(f"TAKE PROFIT, Price: {current_price:.2f}, Profit: {profit_pct:.2f}%")
                    self.order = self.close()

