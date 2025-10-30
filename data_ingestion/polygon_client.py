import pandas as pd
from typing import Optional

from polygon import RESTClient
from config.settings import POLYGON_API_KEY


class PolygonDataClient:
    """Client for fetching financial data from Polygon.io.

    Provides helpers to fetch daily OHLCV bars and convert them into a
    standardized DataFrame with columns: ['Open','High','Low','Close','Volume']
    and a DatetimeIndex in UTC.
    """

    def __init__(self, api_key: Optional[str] = POLYGON_API_KEY):
        if not api_key:
            raise ValueError("Polygon API key is not set.")
        self.client = RESTClient(api_key)

    def get_daily_bars(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical daily OHLCV bars for a given ticker.

        Args:
            ticker: The stock or forex ticker symbol.
            start_date: ISO date 'YYYY-MM-DD'.
            end_date: ISO date 'YYYY-MM-DD'.

        Returns:
            DataFrame with columns ['Open','High','Low','Close','Volume'] indexed by datetime (UTC).
        """
        aggs = self.client.get_aggs(ticker, 1, "day", start_date, end_date)
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
