"""
Forex-specific confluence strategy for major currency pairs.
Optimized for forex market characteristics (24h trading, different volatility).
"""
import backtrader as bt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from data_ingestion.news_client import NewsClient
from backtester.strategies.confluence import ConfluenceStrategy


class ForexConfluenceStrategy(ConfluenceStrategy):
    """
    Confluence strategy optimized for forex markets.
    Major pairs: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
    
    Differences from stock strategy:
    - Adjusted RSI thresholds (forex tends to be more range-bound)
    - Different volume thresholds (forex uses tick volume, not share volume)
    - News sentiment focuses on currency-specific news
    """
    
    params = (
        ("fast_ma", 10),
        ("slow_ma", 50),
        ("rsi_period", 14),
        ("rsi_oversold", 25),  # More sensitive for forex
        ("rsi_overbought", 75),
        ("volume_ma_period", 20),
        ("volume_threshold", 1.15),  # Lower threshold for forex
        ("require_candlestick", True),
        ("require_news", True),
        ("news_sentiment_threshold", 0.05),  # Lower threshold for forex
        ("news_days_back", 7),
        ("min_confirmations", 3),
        ("max_spread_pips", 5),  # Maximum spread in pips (forex-specific)
    )
    
    def __init__(self):
        super().__init__()
        # Forex-specific adjustments can go here
    
    def _get_forex_news_sentiment(self) -> Optional[Dict[str, Any]]:
        """
        Get news sentiment for forex pair.
        For forex, we might need to analyze both base and quote currency news.
        """
        if not self.params.require_news or not self.ticker:
            return None
        
        # Extract base and quote currencies from ticker (e.g., C:EURUSD -> EUR, USD)
        ticker_clean = self.ticker.replace("C:", "").upper()
        if len(ticker_clean) == 6:
            base = ticker_clean[:3]
            quote = ticker_clean[3:]
        else:
            # Fallback: use ticker as-is
            base = ticker_clean
        
        if not self.news_client:
            try:
                self.news_client = NewsClient()
            except Exception:
                return None
        
        current_date = self.data.datetime.date(0) if hasattr(self.data.datetime, 'date') else datetime.utcnow().date()
        date_key = f"{str(current_date)}_{ticker_clean}"
        
        if date_key in self.news_cache:
            return self.news_cache[date_key]
        
        try:
            end_date = current_date.strftime("%Y-%m-%d")
            start_date = (current_date - timedelta(days=self.params.news_days_back)).strftime("%Y-%m-%d")
            
            # Get sentiment for base currency (primary)
            sentiment_base = self.news_client.get_aggregate_sentiment(
                base,
                start_date,
                end_date,
                days_back=self.params.news_days_back,
            )
            
            # Combine with quote currency if available
            sentiment_combined = sentiment_base.copy()
            if len(ticker_clean) == 6:
                try:
                    sentiment_quote = self.news_client.get_aggregate_sentiment(
                        quote,
                        start_date,
                        end_date,
                        days_back=self.params.news_days_back,
                    )
                    # For forex, we want base currency to be bullish relative to quote
                    # Simplified: average the sentiment scores
                    avg_sentiment = (sentiment_base.get("average_sentiment", 0) - 
                                   sentiment_quote.get("average_sentiment", 0)) / 2
                    sentiment_combined["average_sentiment"] = avg_sentiment
                    sentiment_combined["bullish"] = avg_sentiment > self.params.news_sentiment_threshold
                    sentiment_combined["article_count"] = (
                        sentiment_base.get("article_count", 0) + 
                        sentiment_quote.get("article_count", 0)
                    )
                except:
                    pass
            
            self.news_cache[date_key] = sentiment_combined
            return sentiment_combined
        except Exception:
            return None
    
    def _count_confirmations(self):
        """Count confirmations for forex, using forex-specific news sentiment."""
        confirmations = super()._count_confirmations()
        
        # Override news sentiment check with forex-specific method
        if self.params.require_news:
            # Recalculate news confirmation with forex method
            # Remove the news confirmation from parent count and add forex-specific one
            news_sentiment = self._get_forex_news_sentiment()
            # Re-count, replacing news confirmation
            base_count = confirmations
            if news_sentiment and news_sentiment.get("bullish", False):
                if news_sentiment.get("average_sentiment", 0) > self.params.news_sentiment_threshold:
                    # If we already counted news, keep it; otherwise add
                    if base_count < 5:  # Max confirmations
                        confirmations = base_count + 1
        
        return confirmations

