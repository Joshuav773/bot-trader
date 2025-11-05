import backtrader as bt
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from data_ingestion.news_client import NewsClient


class ConfluenceStrategy(bt.Strategy):
    """
    Confluence strategy requiring multiple confirmation points:
    1. Trend confirmation (SMA crossover)
    2. Momentum confirmation (RSI)
    3. Volume confirmation (volume > avg)
    4. Optional: candlestick pattern (hammer, engulfing, etc.)
    """
    
    params = (
        ("fast_ma", 10),
        ("slow_ma", 50),
        ("rsi_period", 14),
        ("rsi_oversold", 30),
        ("rsi_overbought", 70),
        ("volume_ma_period", 20),
        ("volume_threshold", 1.2),  # Volume must be 1.2x average
        ("require_candlestick", True),
        ("require_news", True),
        ("news_sentiment_threshold", 0.1),  # News must be bullish (>0.1)
        ("news_days_back", 7),  # Look at news from last 7 days
        ("min_confirmations", 3),  # Minimum confirmations needed (out of 5: trend, momentum, volume, candlestick, news)
    )
    
    def __init__(self):
        # Trend indicators
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_ma
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_ma
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # Momentum indicator
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        
        # Volume indicator
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.volume_ma_period
        )
        
        # News client (lazy init)
        self.news_client: Optional[NewsClient] = None
        self.ticker: Optional[str] = None
        self.news_cache: Dict[str, Dict[str, Any]] = {}
        
        # Track signals
        self.signals = []
    
    def _check_candlestick_pattern(self):
        """Check for bullish/bearish candlestick patterns."""
        if len(self.data) < 2:
            return False
        
        # Simple hammer detection (long lower wick, small body)
        open_price = self.data.open[0]
        close_price = self.data.close[0]
        high_price = self.data.high[0]
        low_price = self.data.low[0]
        
        body = abs(close_price - open_price)
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        
        # Bullish hammer: long lower wick, small upper wick
        is_hammer = lower_wick >= 2 * body and upper_wick < body
        
        # Bullish engulfing: current candle engulfs previous
        if len(self.data) >= 2:
            prev_open = self.data.open[-1]
            prev_close = self.data.close[-1]
            is_bullish_engulfing = (
                prev_close < prev_open and  # Previous was bearish
                close_price > open_price and  # Current is bullish
                open_price < prev_close and  # Opens below prev close
                close_price > prev_open  # Closes above prev open
            )
            return is_hammer or is_bullish_engulfing
        
        return is_hammer
    
    def _get_news_sentiment(self) -> Optional[Dict[str, Any]]:
        """Get news sentiment for current date. Uses caching to avoid repeated API calls."""
        if not self.params.require_news or not self.ticker:
            return None
        
        if not self.news_client:
            try:
                self.news_client = NewsClient()
            except Exception:
                return None
        
        # Get current date from data
        current_date = self.data.datetime.date(0) if hasattr(self.data.datetime, 'date') else datetime.utcnow().date()
        date_key = str(current_date)
        
        if date_key in self.news_cache:
            return self.news_cache[date_key]
        
        try:
            end_date = current_date.strftime("%Y-%m-%d")
            start_date = (current_date - timedelta(days=self.params.news_days_back)).strftime("%Y-%m-%d")
            
            sentiment_data = self.news_client.get_aggregate_sentiment(
                self.ticker,
                start_date,
                end_date,
                days_back=self.params.news_days_back,
            )
            self.news_cache[date_key] = sentiment_data
            return sentiment_data
        except Exception:
            return None
    
    def _count_confirmations(self):
        """Count how many confirmations are present for a long signal (out of 5)."""
        confirmations = 0
        
        # 1. Trend confirmation: fast MA above slow MA
        if self.fast_ma[0] > self.slow_ma[0]:
            confirmations += 1
        
        # 2. Momentum confirmation: RSI not overbought, bullish momentum
        if self.params.rsi_oversold < self.rsi[0] < self.params.rsi_overbought:
            confirmations += 1
        elif self.rsi[0] > self.params.rsi_oversold:  # Bullish momentum
            confirmations += 1
        
        # 3. Volume confirmation: volume above threshold
        if self.data.volume[0] > self.volume_ma[0] * self.params.volume_threshold:
            confirmations += 1
        
        # 4. Candlestick pattern (if required)
        if self.params.require_candlestick:
            if self._check_candlestick_pattern():
                confirmations += 1
        else:
            # If not required, count it as present (bonus)
            confirmations += 1
        
        # 5. News sentiment confirmation (if required)
        if self.params.require_news:
            news_sentiment = self._get_news_sentiment()
            if news_sentiment and news_sentiment.get("bullish", False):
                if news_sentiment.get("average_sentiment", 0) > self.params.news_sentiment_threshold:
                    confirmations += 1
        else:
            # If not required, count it as present (bonus)
            confirmations += 1
        
        return confirmations
    
    def next(self):
        if not self.position:
            # Look for long entry
            confirmations = self._count_confirmations()
            
            # Additional trend confirmation: recent crossover
            trend_bullish = self.crossover[0] > 0 or self.fast_ma[0] > self.slow_ma[0]
            
            if confirmations >= self.params.min_confirmations and trend_bullish:
                self.buy()
                self.signals.append({
                    "type": "buy",
                    "bar": len(self.data),
                    "confirmations": confirmations,
                    "price": self.data.close[0],
                })
        else:
            # Exit conditions: loss of confirmations or trend reversal
            confirmations = self._count_confirmations()
            trend_bearish = self.crossover[0] < 0 or self.fast_ma[0] < self.slow_ma[0]
            
            if confirmations < self.params.min_confirmations or trend_bearish:
                self.close()
                self.signals.append({
                    "type": "sell",
                    "bar": len(self.data),
                    "confirmations": confirmations,
                    "price": self.data.close[0],
                })

