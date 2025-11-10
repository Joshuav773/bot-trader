"""
Tracks price movements after large orders for impact analysis.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlmodel import Session, select

from api.models import OrderFlow, PriceSnapshot
from config.settings import FINNHUB_API_KEY, POLYGON_API_KEY
from data_ingestion.finnhub_client import FinnhubClient
from data_ingestion.polygon_client import PolygonDataClient


INTERVALS = [1, 5, 15, 60, 1440]  # minutes: 1m, 5m, 15m, 1h, 1d
_FINNHUB_CLIENT: Optional[FinnhubClient] = None


def capture_snapshot(
    order: OrderFlow,
    interval_minutes: int,
    session: Session,
    client: Optional[PolygonDataClient | FinnhubClient] = None,
) -> Optional[PriceSnapshot]:
    """
    Capture price snapshot at a specific interval after a large order.
    """
    snapshot_time = order.timestamp + timedelta(minutes=interval_minutes)

    existing = session.exec(
        select(PriceSnapshot).where(
            PriceSnapshot.order_flow_id == order.id,
            PriceSnapshot.interval_minutes == interval_minutes,
        )
    ).first()
    if existing:
        return existing

    market_client = client or _resolve_market_client()
    if not market_client:
        return None

    try:
        df = _load_bars(market_client, order, snapshot_time)
        if df.empty:
            return None
        df = df.sort_index()
        closest_idx = df.index.get_indexer([snapshot_time], method="pad")
        if closest_idx[0] == -1:
            return None
        snapshot_price = df.iloc[closest_idx[0]]["Close"]

        price_change_pct = ((snapshot_price - order.price) / order.price) * 100

        snapshot = PriceSnapshot(
            order_flow_id=order.id,
            ticker=order.ticker,
            snapshot_time=snapshot_time,
            interval_minutes=interval_minutes,
            price=float(snapshot_price),
            price_change_pct=float(price_change_pct),
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return snapshot
    except Exception:
        return None


def process_snapshots_for_order(
    order: OrderFlow,
    session: Session,
    client: Optional[PolygonDataClient | FinnhubClient] = None,
) -> None:
    """Capture all interval snapshots for a given order."""
    for interval in INTERVALS:
        capture_snapshot(order, interval, session, client)


def _resolve_market_client() -> Optional[PolygonDataClient | FinnhubClient]:
    global _FINNHUB_CLIENT
    if POLYGON_API_KEY:
        try:
            return PolygonDataClient(POLYGON_API_KEY)
        except Exception:
            pass
    if FINNHUB_API_KEY:
        if not _FINNHUB_CLIENT:
            _FINNHUB_CLIENT = FinnhubClient(FINNHUB_API_KEY)
        return _FINNHUB_CLIENT
    return None


def _load_bars(
    market_client: PolygonDataClient | FinnhubClient,
    order: OrderFlow,
    snapshot_time: datetime,
) -> pd.DataFrame:
    start = (snapshot_time - timedelta(days=5)).replace(tzinfo=timezone.utc)
    end = (snapshot_time + timedelta(days=1)).replace(tzinfo=timezone.utc)
    timeframe = "1d"
    symbol = order.ticker
    if order.instrument == "forex":
        timeframe = "1h"
    if isinstance(market_client, FinnhubClient) and order.display_ticker:
        symbol = order.display_ticker
    return market_client.get_bars(symbol, start, end, timeframe=timeframe)

