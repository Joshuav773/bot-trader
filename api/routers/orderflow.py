from typing import List, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session, func
from pydantic import BaseModel

from api.db import get_session
from api.models import OrderFlow, PriceSnapshot
from order_flow.price_tracker import process_snapshots_for_order, INTERVALS
from data_ingestion.polygon_client import PolygonDataClient


router = APIRouter()


class OrderFlowResponse(BaseModel):
    id: int
    ticker: str
    order_type: str
    order_size_usd: float
    price: float
    timestamp: datetime


class PriceImpactResponse(BaseModel):
    order_flow_id: int
    ticker: str
    interval_minutes: int
    price: float
    price_change_pct: float
    snapshot_time: datetime


@router.get("/large-orders", response_model=List[OrderFlowResponse])
def get_large_orders(
    ticker: str | None = Query(None),
    order_type: str | None = Query(None),
    hours: int = Query(24, ge=1, le=168),
    session: Session = Depends(get_session),
):
    """Get large orders (>= $500k) from the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = select(OrderFlow).where(OrderFlow.timestamp >= cutoff)
    
    if ticker:
        query = query.where(OrderFlow.ticker == ticker.upper())
    if order_type:
        query = query.where(OrderFlow.order_type == order_type.lower())
    
    query = query.order_by(OrderFlow.timestamp.desc()).limit(1000)
    orders = session.exec(query).all()
    
    return [OrderFlowResponse(**order.model_dump()) for order in orders]


@router.get("/price-impact/{order_id}", response_model=List[PriceImpactResponse])
def get_price_impact(order_id: int, session: Session = Depends(get_session)):
    """Get price impact snapshots for a specific large order."""
    order = session.get(OrderFlow, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    snapshots = session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.order_flow_id == order_id)
        .order_by(PriceSnapshot.interval_minutes)
    ).all()
    
    return [PriceImpactResponse(**s.model_dump()) for s in snapshots]


@router.get("/price-impact-stats")
def get_price_impact_stats(
    ticker: str | None = Query(None),
    order_type: str | None = Query(None),
    interval_minutes: int = Query(60, ge=1),
    session: Session = Depends(get_session),
):
    """
    Aggregate statistics: average price impact by ticker/type/interval.
    Helps understand: after large buy orders, what's the avg price change at 1h?
    """
    query = select(
        PriceSnapshot.ticker,
        PriceSnapshot.interval_minutes,
        func.avg(PriceSnapshot.price_change_pct).label("avg_change_pct"),
        func.count(PriceSnapshot.id).label("count"),
    ).where(PriceSnapshot.interval_minutes == interval_minutes)
    
    if ticker:
        query = query.where(PriceSnapshot.ticker == ticker.upper())
    
    # Join with OrderFlow to filter by order_type
    if order_type:
        query = query.join(OrderFlow).where(OrderFlow.order_type == order_type.lower())
    
    query = query.group_by(PriceSnapshot.ticker, PriceSnapshot.interval_minutes)
    
    results = session.exec(query).all()
    return [
        {
            "ticker": r.ticker,
            "interval_minutes": r.interval_minutes,
            "avg_price_change_pct": float(r.avg_change_pct),
            "sample_count": r.count,
        }
        for r in results
    ]


@router.post("/trigger-snapshots/{order_id}")
def trigger_snapshots(order_id: int, session: Session = Depends(get_session)):
    """Manually trigger price snapshot capture for an order (for testing)."""
    order = session.get(OrderFlow, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    client = PolygonDataClient()
    process_snapshots_for_order(order, session, client)
    
    return {"message": f"Snapshots triggered for order {order_id}"}

