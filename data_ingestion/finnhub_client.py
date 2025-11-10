import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class FinnhubClient:
    """
    Lightweight Finnhub REST client focused on trades/candles for equities and forex.
    Automatically throttles requests to respect free-tier limits (~60 req/min).
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(
        self,
        api_key: str,
        *,
        max_requests_per_minute: int = 55,
        session: Optional[requests.Session] = None,
    ):
        if not api_key:
            raise ValueError("Finnhub API key must be provided")
        self.api_key = api_key
        self.max_requests_per_minute = max_requests_per_minute
        self.session = session or requests.Session()
        self._request_times: List[float] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def get_stock_trades(self, symbol: str, start: datetime, end: datetime) -> List[Dict]:
        """Fetch raw trades for an equity ticker."""
        params = {
            "symbol": symbol,
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
        }
        data = self._get("/stock/trades", params)
        return data.get("data", []) or []

    def get_forex_trades(self, symbol: str, start: datetime, end: datetime) -> List[Dict]:
        """
        Finnhub does not expose tick-level FX prints on the free tier.
        We synthesize trades from minute candles to approximate flows.
        """
        resolution, start_ts, end_ts = self._resolve_timeframe(start, end)
        params = {
            "symbol": self._to_forex_symbol(symbol),
            "resolution": resolution,
            "from": start_ts,
            "to": end_ts,
        }
        data = self._get("/forex/candle", params)
        trades: List[Dict] = []
        if data.get("s") == "ok":
            timestamps = data.get("t", [])
            closes = data.get("c", [])
            volumes = data.get("v", [])
            for ts, close, volume in zip(timestamps, closes, volumes):
                trades.append(
                    {
                        "timestamp": int(ts) * 1_000_000_000,  # convert seconds to ns
                        "price": close,
                        "volume": volume,
                        "side": "buy",
                    }
                )
        return trades

    def get_index_constituents(self, symbol: str) -> List[str]:
        """Return the list of constituents for an index (e.g., ^GSPC for S&P 500)."""
        data = self._get("/index/constituents", {"symbol": symbol})
        constituents = data.get("constituents") or []
        return [member.upper() for member in constituents]

    def get_bars(self, symbol: str, start: datetime, end: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """Return OHLCV DataFrame similar to Polygon client."""
        path, params = self._bars_params(symbol, start, end, timeframe)
        data = self._get(path, params)
        if data.get("s") != "ok":
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        timestamps = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in data.get("t", [])]
        frame = pd.DataFrame(
            {
                "Open": data.get("o", []),
                "High": data.get("h", []),
                "Low": data.get("l", []),
                "Close": data.get("c", []),
                "Volume": data.get("v", []),
            },
            index=pd.DatetimeIndex(timestamps),
        )
        return frame

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: Dict) -> Dict:
        self._throttle()
        params = dict(params)
        params["token"] = self.api_key
        try:
            resp = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=10)
            if resp.status_code == 429:
                logger.warning("Finnhub rate limit reached. Sleeping for 60s.")
                time.sleep(60)
                resp = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=10)
            resp.raise_for_status()
            self._request_times.append(time.time())
            return resp.json()
        except requests.HTTPError as exc:
            logger.warning("Finnhub request failed (%s): %s", path, exc)
            raise

    def _throttle(self) -> None:
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 60]
        if len(self._request_times) >= self.max_requests_per_minute:
            sleep_for = 60 - (now - self._request_times[0])
            if sleep_for > 0:
                logger.debug("Finnhub throttling for %.2fs to respect rate limits", sleep_for)
                time.sleep(sleep_for)
            # Clean timestamps post-sleep
            now = time.time()
            self._request_times = [t for t in self._request_times if now - t < 60]

    @staticmethod
    def _resolve_timeframe(start: datetime, end: datetime) -> Tuple[str, int, int]:
        """Map interval to minute resolution for candles."""
        delta_seconds = max(int((end - start).total_seconds()), 60)
        if delta_seconds <= 60:
            resolution = "1"
        elif delta_seconds <= 5 * 60:
            resolution = "1"
        elif delta_seconds <= 15 * 60:
            resolution = "5"
        elif delta_seconds <= 30 * 60:
            resolution = "15"
        elif delta_seconds <= 60 * 60:
            resolution = "30"
        elif delta_seconds <= 24 * 60 * 60:
            resolution = "60"
        else:
            resolution = "D"
        return resolution, int(start.timestamp()), int(end.timestamp())

    @staticmethod
    def _to_forex_symbol(pair: str) -> str:
        pair = pair.upper().replace("/", "")
        if len(pair) == 6:
            return f"OANDA:{pair[:3]}_{pair[3:]}"
        return pair

    def _bars_params(self, symbol: str, start: datetime, end: datetime, timeframe: str) -> Tuple[str, Dict]:
        normalized_tf = timeframe.lower()
        resolution_map = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "4h": "240",
            "1d": "D",
        }
        resolution = resolution_map.get(normalized_tf, "D")
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
        }
        path = "/stock/candle"
        if ":" in symbol or symbol.startswith("OANDA"):
            params["symbol"] = self._to_forex_symbol(symbol)
            path = "/forex/candle"
        return path, params

