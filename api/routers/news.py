from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from data_ingestion.news_client import NewsClient


router = APIRouter()


@router.get("/sentiment/{ticker}")
def get_news_sentiment(
    ticker: str,
    days_back: int = Query(7, ge=1, le=30),
) -> Dict[str, Any]:
    """Get aggregate news sentiment for a ticker."""
    try:
        client = NewsClient()
        from datetime import datetime, timedelta
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        sentiment = client.get_aggregate_sentiment(ticker, start_date, end_date, days_back=days_back)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/{ticker}")
def get_news_articles(
    ticker: str,
    days_back: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Get news articles with sentiment for a ticker."""
    try:
        client = NewsClient()
        from datetime import datetime, timedelta
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        articles = client.get_news_for_ticker(ticker, start_date, end_date, limit=limit)
        return articles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

