"""
ForexFactory news client for fetching USD-related forex news.
ForexFactory provides economic calendar and news that's highly relevant for forex trading.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re

from analysis_engine.sentiment_analyzer import SentimentAnalyzer


class ForexFactoryClient:
    """
    Client for fetching news from ForexFactory.
    Focuses on USD-related economic news and events.
    """
    
    def __init__(self):
        self.base_url = "https://www.forexfactory.com"
        self.sentiment_analyzer = SentimentAnalyzer()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_usd_news(
        self,
        days_back: int = 7,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetch USD-related news from ForexFactory.
        
        Args:
            days_back: Number of days to look back
            limit: Maximum articles to return
            
        Returns:
            List of news items with sentiment scores
        """
        try:
            # ForexFactory economic calendar RSS feed
            # Note: ForexFactory doesn't have official API, so we use RSS/calendar
            rss_url = f"{self.base_url}/calendar.php?week=today"
            
            # Try to fetch RSS feed or calendar
            articles = []
            
            # For now, we'll parse the economic calendar page
            # In production, you might want to use their RSS feed if available
            calendar_url = f"{self.base_url}/calendar.php"
            
            try:
                response = self.session.get(calendar_url, timeout=10)
                response.raise_for_status()
                
                # Parse HTML to extract news/events
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # ForexFactory calendar structure - extract events
                # This is a simplified parser - you may need to adjust based on actual HTML structure
                events = self._parse_calendar_events(soup, days_back, limit)
                articles.extend(events)
                
            except Exception as e:
                # Fallback: create placeholder news items
                # In production, you'd want to handle this better
                print(f"Warning: Could not fetch ForexFactory calendar: {e}")
                return []
            
            # Analyze sentiment for each article
            for article in articles:
                text = f"{article.get('title', '')} {article.get('description', '')}".strip()
                if text:
                    try:
                        sentiment = self.sentiment_analyzer.analyze(text)
                        article['sentiment'] = sentiment
                        article['sentiment_score'] = self._calculate_sentiment_score(sentiment)
                    except Exception:
                        article['sentiment'] = {}
                        article['sentiment_score'] = 0.0
            
            return articles[:limit]
            
        except Exception as e:
            print(f"Error fetching ForexFactory news: {e}")
            return []
    
    def _parse_calendar_events(
        self,
        soup: BeautifulSoup,
        days_back: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Parse economic calendar events from ForexFactory HTML.
        ForexFactory's structure may change, so this is a basic parser.
        """
        events = []
        
        try:
            # ForexFactory calendar structure - look for table rows with events
            # The actual structure varies, so we'll try multiple approaches
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Try to find calendar table
            calendar_table = soup.find('table', class_=re.compile('calendar', re.I))
            if not calendar_table:
                calendar_table = soup.find('table', id=re.compile('calendar', re.I))
            
            if calendar_table:
                rows = calendar_table.find_all('tr')
            else:
                # Fallback: look for any table rows
                rows = soup.find_all('tr')[:limit * 2]
            
            for row in rows[:limit * 2]:
                try:
                    # Look for event name/description
                    cells = row.find_all('td')
                    if len(cells) < 3:
                        continue
                    
                    # Try to extract event info (structure may vary)
                    title = ""
                    currency = "USD"
                    impact = "Medium"
                    pub_date = datetime.utcnow()
                    
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        cell_class = cell.get('class', [])
                        
                        # Look for event name
                        if 'event' in str(cell_class).lower() or len(cell_text) > 10:
                            if not title:
                                title = cell_text
                        
                        # Look for currency
                        if len(cell_text) == 3 and cell_text.isupper():
                            currency = cell_text
                    
                    # Filter for USD-related events
                    if currency != "USD" and "USD" not in title.upper() and "US" not in title.upper():
                        continue
                    
                    # Only include if we have a title
                    if not title or len(title) < 5:
                        continue
                    
                    # Only include recent events
                    if pub_date < cutoff_date:
                        continue
                    
                    events.append({
                        "title": title,
                        "description": f"Economic event: {title}",
                        "published_utc": pub_date.isoformat(),
                        "article_url": f"{self.base_url}/calendar.php",
                        "currency": currency,
                        "impact": impact,
                        "source": "ForexFactory",
                    })
                    
                    if len(events) >= limit:
                        break
                        
                except Exception:
                    continue
            
        except Exception as e:
            print(f"Error parsing calendar events: {e}")
        
        return events
    
    def _calculate_sentiment_score(self, sentiment: Dict[str, float]) -> float:
        """
        Calculate a single sentiment score from FinBERT output.
        Returns -1 (very negative) to +1 (very positive).
        """
        positive = sentiment.get("positive", 0.0)
        negative = sentiment.get("negative", 0.0)
        score = positive - negative
        return float(score)
    
    def get_aggregate_sentiment(
        self,
        currency: str = "USD",
        days_back: int = 7,
    ) -> Dict[str, Any]:
        """
        Get aggregate sentiment for USD-related news.
        
        Args:
            currency: Currency to analyze (default: USD)
            days_back: Number of days to look back
            
        Returns:
            Aggregate sentiment data
        """
        articles = self.get_usd_news(days_back=days_back, limit=100)
        
        if not articles:
            return {
                "average_sentiment": 0.0,
                "article_count": 0,
                "bullish": False,
                "bearish": False,
                "source": "ForexFactory",
            }
        
        # Filter for USD-related articles
        usd_articles = [
            a for a in articles
            if currency.upper() in a.get("currency", "").upper() or
            currency.upper() in a.get("title", "").upper()
        ]
        
        if not usd_articles:
            return {
                "average_sentiment": 0.0,
                "article_count": 0,
                "bullish": False,
                "bearish": False,
                "source": "ForexFactory",
            }
        
        scores = [a.get("sentiment_score", 0.0) for a in usd_articles]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "average_sentiment": round(avg_score, 3),
            "article_count": len(usd_articles),
            "bullish": avg_score > 0.1,
            "bearish": avg_score < -0.1,
            "neutral": -0.1 <= avg_score <= 0.1,
            "source": "ForexFactory",
        }

