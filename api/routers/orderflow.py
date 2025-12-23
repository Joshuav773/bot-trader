from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import select, Session
from sqlalchemy import or_
from pydantic import BaseModel, ConfigDict

from api.db import get_session
from api.models import OrderFlow


router = APIRouter()


class OrderFlowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    display_ticker: Optional[str] = None
    order_type: str
    order_side: Optional[str] = None
    instrument: str
    option_type: Optional[str] = None
    contracts: Optional[int] = None
    option_strike: Optional[float] = None
    option_expiration: Optional[datetime] = None
    order_size_usd: float
    size: Optional[float] = None
    price: float
    timestamp: datetime


@router.get("/large-orders", response_model=List[OrderFlowResponse])
def get_large_orders(
    ticker: str | None = Query(None),
    order_type: str | None = Query(None),
    order_side: str | None = Query(None),
    instrument: str | None = Query(None),
    hours: int = Query(24, ge=1, le=168),
    session: Session = Depends(get_session),
):
    """Get large orders (>= $500k) from the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = select(OrderFlow).where(OrderFlow.timestamp >= cutoff)
    
    if ticker:
        ticker_upper = ticker.upper()
        query = query.where(
            or_(OrderFlow.ticker == ticker_upper, OrderFlow.display_ticker == ticker_upper)
        )
    if order_type:
        query = query.where(OrderFlow.order_type == order_type.lower())
    if order_side:
        query = query.where(OrderFlow.order_side == order_side.lower())
    if instrument:
        query = query.where(OrderFlow.instrument == instrument.lower())
    
    query = query.order_by(OrderFlow.timestamp.desc()).limit(1000)
    orders = session.exec(query).all()
    
    return [OrderFlowResponse.model_validate(order) for order in orders]

