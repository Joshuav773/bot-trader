#!/usr/bin/env python3
"""Quick performance check for the optimized streamer."""
from datetime import datetime, timedelta, timezone
from api.db import get_session
from api.models import OrderFlow
from sqlmodel import select, func

session = next(get_session())
now = datetime.now(timezone.utc)

# Get stats for different time windows
windows = [
    ("Last 5 minutes", timedelta(minutes=5)),
    ("Last 30 minutes", timedelta(minutes=30)),
    ("Last hour", timedelta(hours=1)),
    ("Last 24 hours", timedelta(hours=24)),
]

print("📊 Streamer Performance Summary\n")
print("=" * 60)

for label, delta in windows:
    cutoff = now - delta
    count = session.exec(
        select(func.count(OrderFlow.id))
        .where(OrderFlow.timestamp >= cutoff)
    ).one()
    
    # Calculate rate
    hours = delta.total_seconds() / 3600
    rate = count / hours if hours > 0 else 0
    
    print(f"{label:20} | Orders: {count:4} | Rate: {rate:6.1f}/hr")

# Get latest orders
print("\n" + "=" * 60)
print("📈 Latest 5 Orders:\n")

latest = session.exec(
    select(OrderFlow)
    .order_by(OrderFlow.timestamp.desc())
    .limit(5)
).all()

if latest:
    for o in latest:
        age = (now - o.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 60
        print(f"  {o.ticker:6} | ${o.price:8.2f} | ${o.order_size_usd:12,.0f} | {age:5.1f}m ago")
else:
    print("  No orders captured yet")
    print("  (Markets may be closed or no large trades detected)")

# Get ticker distribution
print("\n" + "=" * 60)
print("🏷️  Top 10 Tickers (Last 24h):\n")

cutoff_24h = now - timedelta(hours=24)
ticker_counts = session.exec(
    select(OrderFlow.ticker, func.count(OrderFlow.id).label("count"))
    .where(OrderFlow.timestamp >= cutoff_24h)
    .group_by(OrderFlow.ticker)
    .order_by(func.count(OrderFlow.id).desc())
    .limit(10)
).all()

if ticker_counts:
    for ticker, count in ticker_counts:
        print(f"  {ticker:6} | {count:3} orders")
else:
    print("  No ticker data yet")

print("\n" + "=" * 60)
print("✅ Performance check complete")

