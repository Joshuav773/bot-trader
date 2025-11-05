"""
Tracks price movements after large orders for impact analysis.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from api.models import OrderFlow, PriceSnapshot
from data_ingestion.polygon_client import PolygonDataClient


INTERVALS = [1, 5, 15, 60, 1440]  # minutes: 1m, 5m, 15m, 1h, 1d


def capture_snapshot(order: OrderFlow, interval_minutes: int, session: Session, client: PolygonDataClient) -> Optional[PriceSnapshot]:
    """
    Capture price snapshot at a specific interval after a large order.
    
    Args:
        order: The OrderFlow record
        interval_minutes: Minutes after order execution
        session: DB session
        client: Polygon data client
    
    Returns:
        PriceSnapshot if created, None if data unavailable
    """
    snapshot_time = order.timestamp + timedelta(minutes=interval_minutes)
    
    # Check if already captured
    existing = session.exec(
        select(PriceSnapshot).where(
            PriceSnapshot.order_flow_id == order.id,
            PriceSnapshot.interval_minutes == interval_minutes
        )
    ).first()
    if existing:
        return existing
    
    # Fetch price at snapshot time
    try:
        end = snapshot_time.strftime("%Y-%m-%d")
        start = (snapshot_time - timedelta(days=1)).strftime("%Y-%m-%d")
        df = client.get_daily_bars(order.ticker, start, end)
        if df.empty:
            return None
        
        # Use closest available price
        closest = df.index[df.index <= snapshot_time.replace(tzinfo=None)]
        if len(closest) == 0:
            return None
        snapshot_price = df.loc[closest[-1], "Close"]
        
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


def process_snapshots_for_order(order: OrderFlow, session: Session, client: PolygonDataClient) -> None:
    """Capture all interval snapshots for a given order."""
    for interval in INTERVALS:
        capture_snapshot(order, interval, session, client)

