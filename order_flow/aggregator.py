"""
Filters and aggregates trades to identify large orders >= $500k.
"""
from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
import json

from sqlmodel import Session, select

from api.models import OrderFlow
from config.settings import POLYGON_API_KEY


MIN_ORDER_SIZE_USD = 500_000


def process_trade(trade: Dict, session: Session) -> Optional[OrderFlow]:
    """
    Process a single trade and save if it's >= $500k.
    
    Args:
        trade: Dict with 'ticker', 'price', 'size' (shares), 'side' (buy/sell), 'timestamp'
        session: DB session
    
    Returns:
        OrderFlow if saved, None otherwise
    """
    ticker = trade.get("ticker", "").upper()
    price = float(trade.get("price", 0))
    size = float(trade.get("size", 0))
    side = trade.get("side", "").lower()
    
    if not ticker or price <= 0 or size <= 0:
        return None
    
    order_size_usd = price * size
    
    if order_size_usd < MIN_ORDER_SIZE_USD:
        return None
    
    order_type = "buy" if side in ("buy", "b") else "sell"
    
    # Determine trade timestamp if provided
    trade_time = _parse_timestamp(trade.get("timestamp"))
    if not trade_time:
        trade_time = datetime.utcnow().replace(tzinfo=timezone.utc)

    order = OrderFlow(
        ticker=ticker,
        order_type=order_type,
        order_size_usd=order_size_usd,
        price=price,
        timestamp=trade_time,
        source="polygon",
        raw_data=json.dumps(trade),
    )
    
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def get_sp500_tickers() -> List[str]:
    """Returns S&P 500 ticker list. For now, return a sample; later fetch from external source."""
    # TODO: Fetch from S&P 500 index or maintain list
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
        "V", "JNJ", "WMT", "JPM", "MA", "PG", "UNH", "HD", "DIS", "BAC",
        "ADBE", "NFLX", "CRM", "XOM", "VZ", "CMCSA", "PFE", "KO", "AVGO",
        "COST", "PEP", "TMO", "CSCO", "ABT", "NKE", "MRK", "ACN", "CVX",
        "LIN", "DHR", "WFC", "MCD", "ABBV", "BMY", "PM", "INTU", "TXN",
        "HON", "RTX", "QCOM", "LOW", "AMGN", "SPGI", "GE", "BKNG", "DE",
        "CAT", "ADP", "AXP", "SBUX", "GS", "MDT", "TJX", "ZTS", "ISRG",
        "BLK", "VRTX", "MMC", "CI", "PLD", "REGN", "MO", "AMAT", "SHW",
        "CME", "APH", "KLAC", "SNPS", "CDNS", "FTNT", "MCHP", "NXPI",
        "ADI", "CTSH", "LRCX", "ANSS", "PAYX", "FAST", "IDXX", "CTAS",
        "EXPD", "GLW", "ODFL", "AFL", "FDS", "WST", "ZBRA", "KEYS", "NDAQ",
        "CPRT", "DFS", "FITB", "STT", "HBAN", "RF", "CFG", "MTB", "PNC",
        "TFC", "KEY", "USB", "ZION", "BAC", "JPM", "WFC", "C", "GS", "MS",
    ]


def _parse_timestamp(value: Union[int, float, str, None]) -> Optional[datetime]:
    """Parse polygon trade timestamp values."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            # Polygon timestamps may be in nanoseconds or milliseconds
            if value > 1e15:  # nanoseconds
                return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).replace(tzinfo=None)
            elif value > 1e12:  # microseconds
                return datetime.fromtimestamp(value / 1_000_000, tz=timezone.utc).replace(tzinfo=None)
            elif value > 1e10:  # milliseconds
                return datetime.fromtimestamp(value / 1_000, tz=timezone.utc).replace(tzinfo=None)
            else:
                return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        elif isinstance(value, str):
            # ISO format or numeric string
            if value.isdigit():
                return _parse_timestamp(int(value))
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None
    return None
