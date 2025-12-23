#!/usr/bin/env python3
"""Test the optimized streamer configuration."""
import asyncio
import logging
from datetime import datetime, timezone
from order_flow.streamer import OrderFlowStreamer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_streamer():
    print("🧪 Testing optimized streamer configuration...\n")
    
    streamer = OrderFlowStreamer()
    
    print(f"✓ Streamer initialized:")
    print(f"  Provider: {streamer.provider}")
    print(f"  Poll Interval: {streamer.poll_interval}s")
    print(f"  Lookback: {streamer.lookback_minutes} minutes")
    print(f"  Equity Batches: {len(streamer.equity_batches)}")
    print(f"  Total S&P 500 Tickers: {sum(len(b) for b in streamer.equity_batches)}")
    print(f"  Forex Batches: {len(streamer.forex_batches)} (should be 0)\n")
    
    # Run a few poll cycles to test
    print("🔄 Running 3 poll cycles to test performance...\n")
    for i in range(3):
        print(f"--- Poll Cycle {i+1} ---")
        start = datetime.now(timezone.utc)
        try:
            await streamer._poll_recent_trades()
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            print(f"✓ Completed in {elapsed:.2f}s\n")
        except Exception as e:
            print(f"✗ Failed: {e}\n")
            import traceback
            traceback.print_exc()
            break
        await asyncio.sleep(2)  # Small delay between test cycles
    
    # Check for captured orders
    print("\n📊 Checking for captured orders...")
    from api.db import get_session
    from api.models import OrderFlow
    from sqlmodel import select
    from datetime import timedelta
    
    session = next(get_session())
    recent = datetime.now(timezone.utc) - timedelta(minutes=5)
    orders = session.exec(
        select(OrderFlow)
        .where(OrderFlow.timestamp >= recent)
        .order_by(OrderFlow.timestamp.desc())
        .limit(10)
    ).all()
    
    print(f"  Orders captured in last 5 minutes: {len(orders)}")
    if orders:
        for o in orders[:5]:
            print(f"    • {o.ticker} | ${o.price:.2f} | ${o.order_size_usd:,.0f} | {o.timestamp.strftime('%H:%M:%S')}")
    else:
        print("    No orders yet (markets may be closed or no large trades)")
    
    print("\n✅ Streamer test complete!")

if __name__ == "__main__":
    asyncio.run(test_streamer())

