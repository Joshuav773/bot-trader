from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_user_email"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    password_hash: str
    is_master: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderFlow(SQLModel, table=True):
    """Tracks large orders (>= 500k) for S&P 500 tickers."""
    __tablename__ = "order_flow"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    order_type: str = Field(index=True)  # 'buy' or 'sell'
    order_size_usd: float = Field(index=True)  # Total USD value
    price: float  # Execution price
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    source: str = Field(default="polygon")  # 'polygon' or 'alpaca'
    raw_data: Optional[str] = None  # JSON for debugging


class PriceSnapshot(SQLModel, table=True):
    """Tracks price movements after large orders for impact analysis."""
    __tablename__ = "price_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_flow_id: int = Field(foreign_key="order_flow.id", index=True)
    ticker: str = Field(index=True)
    snapshot_time: datetime = Field(default_factory=datetime.utcnow, index=True)
    interval_minutes: int = Field(index=True)  # 1, 5, 15, 60, 1440 (1d)
    price: float
    price_change_pct: float  # % change from order execution price
