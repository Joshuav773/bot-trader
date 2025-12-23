#!/usr/bin/env python3
"""Monitor streamer performance and captured orders."""
import time
from datetime import datetime, timedelta, timezone
from api.db import get_session
from api.models import OrderFlow
from sqlmodel import select, func

def monitor():
    print("📊 Streamer Performance Monitor\n")
    print("Press Ctrl+C to stop\n")
    
    session = next(get_session())
    last_count = 0
    start_time = datetime.now(timezone.utc)
    
    try:
        while True:
            now = datetime.now(timezone.utc)
            elapsed = (now - start_time).total_seconds()
            
            # Count orders in last hour
            cutoff = now - timedelta(hours=1)
            total_orders = session.exec(
                select(func.count(OrderFlow.id))
                .where(OrderFlow.timestamp >= cutoff)
            ).one()
            
            # Count orders in last 10 minutes
            recent_cutoff = now - timedelta(minutes=10)
            recent_orders = session.exec(
                select(func.count(OrderFlow.id))
                .where(OrderFlow.timestamp >= cutoff)
                .where(OrderFlow.timestamp >= recent_cutoff)
            ).one()
            
            # Get latest orders
            latest = session.exec(
                select(OrderFlow)
                .order_by(OrderFlow.timestamp.desc())
                .limit(5)
            ).all()
            
            new_orders = total_orders - last_count
            rate = total_orders / (elapsed / 3600) if elapsed > 0 else 0
            
            print(f"\r⏱  Runtime: {int(elapsed/60)}m | "
                  f"Total (1h): {total_orders} | "
                  f"Recent (10m): {recent_orders} | "
                  f"New: +{new_orders} | "
                  f"Rate: {rate:.1f}/hr", end="", flush=True)
            
            if latest:
                latest_ticker = latest[0].ticker
                latest_time = latest[0].timestamp.strftime("%H:%M:%S")
                print(f" | Latest: {latest_ticker} @ {latest_time}", end="", flush=True)
            
            last_count = total_orders
            time.sleep(10)  # Update every 10 seconds
            
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped")

if __name__ == "__main__":
    monitor()

