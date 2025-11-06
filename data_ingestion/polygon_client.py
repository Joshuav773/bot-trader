import logging
import os
import time
from typing import Optional, Tuple

import pandas as pd

# Robust import for Polygon REST client across package variants
try:
    from polygon import RESTClient  # polygon-api-client preferred
except Exception:  # pragma: no cover
    try:
        from polygon.rest import RESTClient  # alternate path in some versions
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "Polygon REST client not found. Install with: pip install polygon-api-client"
        ) from e

from config.settings import POLYGON_API_KEY

logger = logging.getLogger(__name__)


class PolygonDataClient:
    """Client for fetching financial data from Polygon.io.

    Provides helpers to fetch daily OHLCV bars and convert them into a
    standardized DataFrame with columns: ['Open','High','Low','Close','Volume']
    and a DatetimeIndex in UTC.
    """

    def __init__(
        self,
        api_key: Optional[str] = POLYGON_API_KEY,
        *,
        retries: Optional[int] = None,
        backoff_seconds: Optional[float] = None,
        read_timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
    ):
        if not api_key:
            raise ValueError("Polygon API key is not set.")
        self.retries = retries or int(os.getenv("POLYGON_MAX_RETRIES", "3"))
        self.backoff_seconds = backoff_seconds or float(os.getenv("POLYGON_RETRY_BACKOFF", "1.5"))
        rt = read_timeout or float(os.getenv("POLYGON_READ_TIMEOUT", "15"))
        ct = connect_timeout or float(os.getenv("POLYGON_CONNECT_TIMEOUT", "5"))
        try:
            self.client = RESTClient(
                api_key,
                read_timeout=rt,
                connect_timeout=ct,
            )
        except TypeError:
            # Older versions of polygon-api-client may not support timeout kwargs
            logger.warning("Polygon RESTClient does not support timeout parameters, proceeding without custom timeouts.")
            self.client = RESTClient(api_key)

    def normalize_forex_ticker(self, ticker: str) -> str:
        """
        Normalize forex ticker to Polygon format.
        Converts EURUSD -> C:EURUSD, or leaves as-is if already formatted.
        """
        ticker = ticker.upper().replace("/", "")
        if not ticker.startswith("C:"):
            return f"C:{ticker}"
        return ticker
    
    def is_forex_ticker(self, ticker: str) -> bool:
        """Check if ticker is a forex pair."""
        return ticker.startswith("C:") or "/" in ticker.upper() or len(ticker.replace("/", "")) == 6
    
    def get_bars(self, ticker: str, start_date: str, end_date: str, timeframe: str = "1d") -> pd.DataFrame:
        """
        Fetch historical OHLCV bars for a given ticker and timeframe.

        Args:
            ticker: The stock or forex ticker symbol (forex: EURUSD or C:EURUSD).
            start_date: ISO date 'YYYY-MM-DD' or datetime 'YYYY-MM-DD HH:MM:SS'.
            end_date: ISO date 'YYYY-MM-DD' or datetime 'YYYY-MM-DD HH:MM:SS'.
            timeframe: One of '1d', '4h', '1h', '30m', '15m', '5m'.

        Returns:
            DataFrame with columns ['Open','High','Low','Close','Volume'] indexed by datetime (UTC).
        """
        # Normalize forex tickers
        if self.is_forex_ticker(ticker):
            ticker = self.normalize_forex_ticker(ticker)
        
        # Parse timeframe
        multiplier, timespan = self._parse_timeframe(timeframe)
        
        aggs = self._get_aggs_with_retry(ticker, multiplier, timespan, start_date, end_date)
        if not aggs:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"]).astype({
                "Open": "float64", "High": "float64", "Low": "float64", "Close": "float64", "Volume": "float64"
            })

        records = []
        for a in aggs:
            o = getattr(a, "o", None) if hasattr(a, "o") else getattr(a, "open", None)
            h = getattr(a, "h", None) if hasattr(a, "h") else getattr(a, "high", None)
            l = getattr(a, "l", None) if hasattr(a, "l") else getattr(a, "low", None)
            c = getattr(a, "c", None) if hasattr(a, "c") else getattr(a, "close", None)
            v = getattr(a, "v", None) if hasattr(a, "v") else getattr(a, "volume", None)
            t = getattr(a, "t", None) if hasattr(a, "t") else getattr(a, "timestamp", None)
            records.append({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v, "timestamp": t})

        df = pd.DataFrame.from_records(records)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("datetime", inplace=True)
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        return df.sort_index()
    
    def _parse_timeframe(self, timeframe: str) -> Tuple[int, str]:
        """
        Parse timeframe string into Polygon API format.
        
        Args:
            timeframe: '1d', '4h', '1h', '30m', '15m', '5m'
        
        Returns:
            (multiplier, timespan) tuple for Polygon API
        """
        timeframe_lower = timeframe.lower()
        
        if timeframe_lower == "1d" or timeframe_lower == "day":
            return (1, "day")
        elif timeframe_lower == "4h" or timeframe_lower == "4hour":
            return (4, "hour")
        elif timeframe_lower == "1h" or timeframe_lower == "hour":
            return (1, "hour")
        elif timeframe_lower == "30m" or timeframe_lower == "30min":
            return (30, "minute")
        elif timeframe_lower == "15m" or timeframe_lower == "15min":
            return (15, "minute")
        elif timeframe_lower == "5m" or timeframe_lower == "5min":
            return (5, "minute")
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Use: 1d, 4h, 1h, 30m, 15m, 5m")
    
    def get_daily_bars(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical daily OHLCV bars for a given ticker (backwards compatibility).

        Args:
            ticker: The stock or forex ticker symbol (forex: EURUSD or C:EURUSD).
            start_date: ISO date 'YYYY-MM-DD'.
            end_date: ISO date 'YYYY-MM-DD'.

        Returns:
            DataFrame with columns ['Open','High','Low','Close','Volume'] indexed by datetime (UTC).
        """
        return self.get_bars(ticker, start_date, end_date, timeframe="1d")

    def _get_aggs_with_retry(self, ticker: str, multiplier: int, timespan: str, start_date: str, end_date: str):
        """Call Polygon get_aggs with retry + exponential backoff."""
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                return self.client.get_aggs(ticker, multiplier, timespan, start_date, end_date)
            except Exception as exc:  # broad catch but we re-raise with context
                last_error = exc
                wait_time = self.backoff_seconds * attempt
                logger.warning(
                    "Polygon get_aggs failed (attempt %s/%s) for %s %s %s-%s: %s",
                    attempt,
                    self.retries,
                    ticker,
                    timespan,
                    start_date,
                    end_date,
                    exc,
                )
                if attempt < self.retries:
                    time.sleep(wait_time)
        raise RuntimeError(f"Polygon API error: {last_error}") from last_error
