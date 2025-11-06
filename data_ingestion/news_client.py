"""
News data client for fetching financial news and sentiment analysis.
Uses Polygon.io news API, ForexFactory (for forex), and FinBERT for sentiment scoring.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from polygon import RESTClient
from analysis_engine.sentiment_analyzer import SentimentAnalyzer
from config.settings import POLYGON_API_KEY
from data_ingestion.forexfactory_client import ForexFactoryClient


class NewsClient:
    """Client for fetching and analyzing financial news."""
    
    def __init__(self, api_key: Optional[str] = POLYGON_API_KEY, use_forexfactory: bool = False):
        self.use_forexfactory = use_forexfactory
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Initialize Polygon client if API key available
        if api_key:
            try:
                self.client = RESTClient(api_key)
                self.has_polygon = True
            except:
                self.client = None
                self.has_polygon = False
        else:
            self.client = None
            self.has_polygon = False
        
        # Initialize ForexFactory client if requested
        if use_forexfactory:
            try:
                self.forexfactory_client = ForexFactoryClient()
                self.has_forexfactory = True
            except:
                self.forexfactory_client = None
                self.has_forexfactory = False
        else:
            self.forexfactory_client = None
            self.has_forexfactory = False
    
    def get_news_for_ticker(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles for a ticker and analyze sentiment.
        
        For forex pairs (e.g., EURUSD), uses ForexFactory if enabled.
        For stocks, uses Polygon.io.
        
        Args:
            ticker: Stock ticker symbol or forex pair (e.g., EURUSD)
            start_date: ISO date 'YYYY-MM-DD'
            end_date: ISO date 'YYYY-MM-DD'
            limit: Max articles to fetch
        
        Returns:
            List of news items with sentiment scores
        """
        articles = []
        
        # Check if this is a forex pair (no colon prefix, or contains currency codes)
        is_forex = (
            len(ticker) == 6 and ticker.isalpha() and ticker.isupper() or
            ticker.startswith("C:") or
            "USD" in ticker.upper()
        )
        
        # Use ForexFactory for forex pairs if enabled
        if is_forex and self.has_forexfactory and self.forexfactory_client:
            try:
                days_back = (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days
                forexfactory_news = self.forexfactory_client.get_usd_news(
                    days_back=max(days_back, 7),
                    limit=limit
                )
                articles.extend(forexfactory_news)
            except Exception as e:
                print(f"ForexFactory fetch failed: {e}")
        
        # Use Polygon for stocks or as fallback
        if self.has_polygon and self.client:
            try:
                # Polygon news API
                news = self.client.list_ticker_news(ticker=ticker, limit=limit)
                
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
                
                polygon_articles = []
                for item in news:
                    # Filter by date range
                    pub_date = item.published_utc
                    if isinstance(pub_date, str):
                        try:
                            pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00').replace('+00:00', ''))
                        except:
                            pub_date = datetime.fromisoformat(pub_date.split('T')[0])
                    
                    if isinstance(pub_date, datetime):
                        pub_date_naive = pub_date.replace(tzinfo=None)
                        if pub_date_naive < start_dt or pub_date_naive > end_dt:
                            continue
                    
                    # Combine title and description for sentiment
                    text = f"{item.title or ''} {item.description or ''}".strip()
                    
                    if not text:
                        continue
                    
                    # Analyze sentiment
                    sentiment = self.sentiment_analyzer.analyze(text)
                    
                    polygon_articles.append({
                        "title": item.title,
                        "description": item.description,
                        "published_utc": item.published_utc,
                        "article_url": item.article_url,
                        "sentiment": sentiment,
                        "sentiment_score": self._calculate_sentiment_score(sentiment),
                    })
                
                articles.extend(polygon_articles)
            except Exception as e:
                print(f"Polygon news fetch failed: {e}")
        
        return articles[:limit]
    
    def _calculate_sentiment_score(self, sentiment: Dict[str, float]) -> float:
        """
        Calculate a single sentiment score from FinBERT output.
        Returns -1 (very negative) to +1 (very positive).
        """
        # FinBERT typically has: positive, negative, neutral
        positive = sentiment.get("positive", 0.0)
        negative = sentiment.get("negative", 0.0)
        neutral = sentiment.get("neutral", 0.0)
        
        # Weighted score: positive - negative, normalized
        score = positive - negative
        return float(score)
    
    def get_aggregate_sentiment(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        days_back: int = 7,
    ) -> Dict[str, Any]:
        """
        Get aggregate sentiment for a ticker over a time period.
        Returns average sentiment score and article count.
        
        For forex pairs, prioritizes ForexFactory if enabled.
        """
        # Check if forex pair
        is_forex = (
            len(ticker.replace("C:", "")) == 6 and ticker.replace("C:", "").isalpha() or
            "USD" in ticker.upper()
        )
        
        # Use ForexFactory for forex if enabled
        if is_forex and self.has_forexfactory and self.forexfactory_client:
            try:
                # Extract currency if needed (e.g., EURUSD -> USD)
                currency = "USD"  # Default to USD for ForexFactory
                if "USD" in ticker.upper():
                    currency = "USD"
                
                return self.forexfactory_client.get_aggregate_sentiment(
                    currency=currency,
                    days_back=days_back,
                )
            except Exception as e:
                print(f"ForexFactory sentiment failed: {e}")
        
        # Fallback to Polygon or regular method
        # Calculate date range
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except:
            end_dt = datetime.fromisoformat(end_date)
        start_dt = end_dt - timedelta(days=days_back)
        
        articles = self.get_news_for_ticker(
            ticker,
            start_dt.strftime("%Y-%m-%d"),
            end_dt.strftime("%Y-%m-%d"),
            limit=100,
        )
        
        if not articles:
            return {
                "average_sentiment": 0.0,
                "article_count": 0,
                "bullish": False,
                "bearish": False,
            }
        
        scores = [a["sentiment_score"] for a in articles]
        avg_score = sum(scores) / len(scores)
        
        return {
            "average_sentiment": round(avg_score, 3),
            "article_count": len(articles),
            "bullish": avg_score > 0.1,  # Positive sentiment threshold
            "bearish": avg_score < -0.1,  # Negative sentiment threshold
            "neutral": -0.1 <= avg_score <= 0.1,
        }

