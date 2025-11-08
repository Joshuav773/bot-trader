"""
Filters and aggregates trades to identify large orders >= $500k.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

import requests
from sqlmodel import Session

from api.models import OrderFlow
from config.settings import POLYGON_API_KEY


logger = logging.getLogger(__name__)

MIN_ORDER_SIZE_USD = 500_000
_SP500_CACHE: Dict[str, Union[float, List[str]]] = {"expires_at": 0.0, "tickers": []}
_SP500_CACHE_LOCK = threading.Lock()
_SP500_CACHE_TTL_SECONDS = 60 * 60 * 6  # refresh every 6 hours

MAJOR_FOREX_PAIRS: List[str] = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
    "NZDUSD",
    "EURJPY",
    "EURGBP",
    "EURCHF",
    "GBPJPY",
    "USDHKD",
    "USDNOK",
    "USDSEK",
    "USDSGD",
    "USDTRY",
    "USDMXN",
    "USDZAR",
    "XAUUSD",
    "XAGUSD",
]
_MAJOR_FOREX_SET = {pair.upper() for pair in MAJOR_FOREX_PAIRS}

# Fallback subset to guarantee we always have a baseline universe
_FALLBACK_SP500 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "V", "JNJ",
    "WMT", "JPM", "MA", "PG", "UNH", "HD", "DIS", "BAC", "ADBE", "NFLX",
    "CRM", "XOM", "KO", "PEP", "COST", "PFE", "CSCO", "MRK", "AVGO", "ABBV",
    "ACN", "CVX", "INTU", "TXN", "LOW", "QCOM", "AMD", "AMGN", "HON", "SPGI",
    "GS", "MCD", "SBUX", "CAT", "DE", "AMAT", "LRCX", "ZTS", "VRTX", "BKNG",
]


def process_trade(trade: Dict, session: Session) -> Optional[OrderFlow]:
    """
    Process a single trade and save if it's >= $500k.

    Args:
        trade: Dict with 'ticker', 'price', 'size' (shares), 'side' (buy/sell), 'timestamp'
        session: DB session

    Returns:
        OrderFlow if saved, None otherwise
    """
    original_ticker = trade.get("ticker", "")
    ticker = original_ticker.upper()
    price = float(trade.get("price", 0))
    size = float(trade.get("size", 0))
    side = trade.get("side", "").lower()

    if not ticker or price <= 0 or size <= 0:
        return None

    instrument = _detect_instrument(ticker)
    display_ticker = _display_ticker_for(ticker, instrument)
    option_meta = _parse_option_metadata(ticker) if instrument == "option" else {}
    contracts = option_meta.get("contracts")
    option_type = option_meta.get("option_type")
    option_strike = option_meta.get("option_strike")
    option_expiration = option_meta.get("option_expiration")

    # For options, size is contracts and notional should include contract multiplier (100)
    contracts = int(size) if instrument == "option" else contracts
    notional_multiplier = 100.0 if instrument == "option" else 1.0

    order_size_usd = price * size * notional_multiplier

    if order_size_usd < MIN_ORDER_SIZE_USD:
        return None

    order_side = "buy" if side in ("buy", "b") else "sell"
    order_type = option_type if option_type else order_side

    # Determine trade timestamp if provided
    trade_time = _parse_timestamp(trade.get("timestamp"))
    if not trade_time:
        trade_time = datetime.utcnow().replace(tzinfo=timezone.utc)

    order = OrderFlow(
        ticker=ticker,
        display_ticker=display_ticker,
        order_type=order_type,
        order_side=order_side,
        instrument=instrument,
        option_type=option_type,
        contracts=contracts,
        option_strike=option_strike,
        option_expiration=option_expiration,
        order_size_usd=order_size_usd,
        price=price,
        size=size,
        timestamp=trade_time,
        source="polygon",
        raw_data=json.dumps(trade),
    )

    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def get_sp500_tickers() -> List[str]:
    """
    Return the current S&P 500 constituents. Falls back to a static subset
    if Polygon is unavailable.
    """
    now = time.time()

    with _SP500_CACHE_LOCK:
        if (
            _SP500_CACHE["tickers"]
            and isinstance(_SP500_CACHE["expires_at"], (int, float))
            and now < _SP500_CACHE["expires_at"]
        ):
            return list(_SP500_CACHE["tickers"])  # copy

    tickers: List[str] = []
    if POLYGON_API_KEY:
        try:
            tickers = _fetch_sp500_from_polygon()
        except Exception as exc:  # pragma: no cover - external service
            logger.warning("Failed to refresh S&P 500 tickers from Polygon: %s", exc)

    if not tickers:
        tickers = list(_FALLBACK_SP500)

    with _SP500_CACHE_LOCK:
        _SP500_CACHE["tickers"] = tickers
        _SP500_CACHE["expires_at"] = now + _SP500_CACHE_TTL_SECONDS

    return tickers


def get_major_forex_pairs() -> List[str]:
    """Return the default universe of major forex pairs."""
    return list(MAJOR_FOREX_PAIRS)


def _fetch_sp500_from_polygon() -> List[str]:
    """Fetch the latest S&P 500 list from Polygon Reference API."""
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "market": "stocks",
        "active": "true",
        "limit": 1000,
        "index": "sp500",
        "apiKey": POLYGON_API_KEY,
    }
    tickers: List[str] = []
    next_url: Optional[str] = url

    while next_url:
        response = requests.get(next_url, params=params if next_url == url else None, timeout=10)
        response.raise_for_status()
        data = response.json()
        tickers.extend(result["ticker"] for result in data.get("results", []) if result.get("ticker"))
        next_url = data.get("next_url")
        if next_url:
            # next_url may already contain the apiKey; ensure it's present
            if "apiKey=" not in next_url:
                next_url = f"{next_url}&apiKey={POLYGON_API_KEY}"
        params = None  # only for first request

    # Deduplicate and sort for stability
    deduped = sorted({ticker.upper() for ticker in tickers})
    return deduped


def _detect_instrument(ticker: str) -> str:
    if ticker.startswith("O:"):
        return "option"
    normalized = ticker.replace("C:", "")
    if normalized in _MAJOR_FOREX_SET:
        return "forex"
    return "equity"


def _display_ticker_for(ticker: str, instrument: str) -> str:
    if instrument == "forex":
        return ticker.replace("C:", "")
    if instrument == "option":
        meta = _parse_option_metadata(ticker)
        underlying = meta.get("underlying")
        if underlying:
            return underlying
    return ticker


def _parse_option_metadata(ticker: str) -> Dict[str, Optional[Union[str, int, float, datetime]]]:
    """
    Parse Polygon option ticker format:
    O:<UNDERLYING><YYMMDD><C/P><STRIKE * 1000>
    """
    meta: Dict[str, Optional[Union[str, int, float, datetime]]] = {
        "underlying": None,
        "option_type": None,
        "option_strike": None,
        "option_expiration": None,
        "contracts": None,
    }

    if not ticker.startswith("O:"):
        return meta

    try:
        body = ticker.split(":", 1)[1]
        idx = 0
        while idx < len(body) and body[idx].isalpha():
            idx += 1
        underlying = body[:idx]
        remaining = body[idx:]
        if len(remaining) < 7:
            return meta

        date_part = remaining[:6]
        option_flag = remaining[6]
        strike_part = remaining[7:]

        expiration = datetime.strptime(date_part, "%y%m%d")
        option_type = "call" if option_flag.upper() == "C" else "put" if option_flag.upper() == "P" else None
        strike = None
        if strike_part and strike_part.isdigit():
            strike = int(strike_part) / 1000.0

        meta.update(
            {
                "underlying": underlying,
                "option_type": option_type,
                "option_strike": strike,
                "option_expiration": expiration,
            }
        )
    except Exception as exc:  # pragma: no cover - parsing guard
        logger.debug("Failed to parse option ticker %s: %s", ticker, exc)

    return meta


def _parse_timestamp(value: Union[int, float, str, None]) -> Optional[datetime]:
    """Parse polygon trade timestamp values."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            # Polygon timestamps may be in nanoseconds or milliseconds
            if value > 1e15:  # nanoseconds
                return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).replace(tzinfo=None)
            if value > 1e12:  # microseconds
                return datetime.fromtimestamp(value / 1_000_000, tz=timezone.utc).replace(tzinfo=None)
            if value > 1e10:  # milliseconds
                return datetime.fromtimestamp(value / 1_000, tz=timezone.utc).replace(tzinfo=None)
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        if isinstance(value, str):
            # ISO format or numeric string
            if value.isdigit():
                return _parse_timestamp(int(value))
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None
    return None
