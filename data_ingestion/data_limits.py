"""
Utility to get data limits based on timeframe.
This module provides a centralized way to manage Polygon.io API data limits.
"""
from typing import Dict
from datetime import datetime, timedelta
from config.settings import POLYGON_DATA_LIMITS


def get_start_date_for_timeframe(timeframe: str) -> str:
    """
    Get appropriate start date based on configured data limits for the timeframe.
    
    Args:
        timeframe: Timeframe string (1d, 4h, 1h, 30m, 15m, 5m)
    
    Returns:
        ISO date string (YYYY-MM-DD) for the start date
    """
    tf_lower = timeframe.lower()
    
    # Normalize timeframe aliases
    if tf_lower in ["1d", "day"]:
        tf_key = "1d"
    elif tf_lower in ["4h", "4hour"]:
        tf_key = "4h"
    elif tf_lower in ["1h", "hour"]:
        tf_key = "1h"
    elif tf_lower in ["30m", "30min"]:
        tf_key = "30m"
    elif tf_lower in ["15m", "15min"]:
        tf_key = "15m"
    elif tf_lower in ["5m", "5min"]:
        tf_key = "5m"
    else:
        # Default to daily limits for unknown timeframes
        tf_key = "1d"
    
    # Get limit in days
    limit_days = POLYGON_DATA_LIMITS.get(tf_key, 730)
    
    # Calculate start date
    date = datetime.now()
    if limit_days >= 365:
        # For years, use setFullYear
        years = limit_days // 365
        date = date.replace(year=date.year - years)
    else:
        # For days, use timedelta
        date = date - timedelta(days=limit_days)
    
    return date.strftime("%Y-%m-%d")


def get_data_limits() -> Dict[str, int]:
    """
    Get all configured data limits.
    
    Returns:
        Dictionary mapping timeframe to limit in days
    """
    return POLYGON_DATA_LIMITS.copy()

