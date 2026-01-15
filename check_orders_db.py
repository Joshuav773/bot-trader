"""
Check Orders Database
=====================

Verifies that orders are being properly saved to the database.

Usage:
    python3 check_orders_db.py
    python3 check_orders_db.py --hours 1
    python3 check_orders_db.py --recent
"""
import os
import sys
import logging
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from db import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.error("Database module not available")


def check_database(hours: int = 24, recent_only: bool = False):
    """Check database for orders and trades"""
    if not DB_AVAILABLE:
        logger.error("Database module not available")
        return False
    
    db = get_db()
    
    if not db.connect():
        logger.error("Failed to connect to database")
        return False
    
    try:
        cursor = db.conn.cursor()
        
        logger.info("=" * 100)
        logger.info("🔍 CHECKING ORDER_FLOW DATABASE")
        logger.info("=" * 100)
        logger.info("")
        
        # Get time threshold
        if recent_only:
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
            logger.info(f"📅 Checking last 1 hour only")
        else:
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
            logger.info(f"📅 Checking last {hours} hour(s)")
        
        logger.info(f"   From: {time_threshold.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"   To:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("")
        
        # Count total entries
        cursor.execute("SELECT COUNT(*) FROM order_flow")
        total_count = cursor.fetchone()[0]
        logger.info(f"📊 Total entries in order_flow table: {total_count:,}")
        
        # Count recent entries
        cursor.execute("""
            SELECT COUNT(*) 
            FROM order_flow 
            WHERE timestamp >= %s
        """, (time_threshold,))
        recent_count = cursor.fetchone()[0]
        logger.info(f"📊 Entries in last {hours if not recent_only else 1} hour(s): {recent_count:,}")
        logger.info("")
        
        # Breakdown by order_type
        cursor.execute("""
            SELECT order_type, COUNT(*) as count
            FROM order_flow
            WHERE timestamp >= %s
            GROUP BY order_type
            ORDER BY count DESC
        """, (time_threshold,))
        
        logger.info("📋 Breakdown by order type:")
        type_counts = {}
        for row in cursor.fetchall():
            order_type = row[0]
            count = row[1]
            type_counts[order_type] = count
            logger.info(f"   {order_type}: {count:,}")
        
        logger.info("")
        
        # Breakdown by source
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM order_flow
            WHERE timestamp >= %s
            GROUP BY source
            ORDER BY count DESC
        """, (time_threshold,))
        
        logger.info("📋 Breakdown by source:")
        for row in cursor.fetchall():
            source = row[0]
            count = row[1]
            logger.info(f"   {source}: {count:,}")
        
        logger.info("")
        
        # Get recent orders (last 10)
        cursor.execute("""
            SELECT 
                id, ticker, order_type, order_size_usd, price, timestamp, 
                source, raw_data, instrument, order_side
            FROM order_flow
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            LIMIT 10
        """, (time_threshold,))
        
        recent_orders = cursor.fetchall()
        
        if recent_orders:
            logger.info("=" * 100)
            logger.info(f"📋 RECENT ORDERS (Last 10)")
            logger.info("=" * 100)
            logger.info("")
            logger.info(f"{'#':<4} {'Time':<20} {'Symbol':<8} {'Type':<20} {'Value (USD)':<15} {'Price':<12} {'Side':<8}")
            logger.info("-" * 100)
            
            for i, row in enumerate(recent_orders, 1):
                order_id = row[0]
                ticker = row[1] or 'N/A'
                order_type = row[2] or 'N/A'
                order_size = float(row[3]) if row[3] else 0
                price = float(row[4]) if row[4] else None
                timestamp = row[5]
                source = row[6] or 'N/A'
                raw_data = row[7]
                instrument = row[8] or 'N/A'
                order_side = row[9] or 'N/A'
                
                # Format timestamp
                if isinstance(timestamp, datetime):
                    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    time_str = str(timestamp)[:19]
                
                # Parse order type to show BUY/SELL
                display_type = order_type
                if 'buy' in order_type.lower():
                    display_type = f"BUY ({order_type})"
                elif 'sell' in order_type.lower():
                    display_type = f"SELL ({order_type})"
                
                print(f"{i:2d}.  {time_str:<20} {ticker:<8} {display_type:<20} "
                      f"${order_size:>13,.2f}  ${price:>10.2f if price else 'N/A':<12} {order_side:<8}")
            
            logger.info("-" * 100)
            logger.info("")
            
            # Show details of most recent order
            if recent_orders:
                logger.info("=" * 100)
                logger.info("📋 MOST RECENT ORDER DETAILS")
                logger.info("=" * 100)
                logger.info("")
                
                row = recent_orders[0]
                order_id = row[0]
                ticker = row[1] or 'N/A'
                order_type = row[2] or 'N/A'
                order_size = float(row[3]) if row[3] else 0
                price = float(row[4]) if row[4] else None
                timestamp = row[5]
                source = row[6] or 'N/A'
                raw_data = row[7]
                instrument = row[8] or 'N/A'
                order_side = row[9] or 'N/A'
                
                logger.info(f"ID: {order_id}")
                logger.info(f"Symbol: {ticker}")
                logger.info(f"Order Type: {order_type}")
                logger.info(f"Order Side: {order_side}")
                logger.info(f"Value: ${order_size:,.2f}")
                logger.info(f"Price: ${price:.2f}" if price else "Price: N/A")
                logger.info(f"Instrument: {instrument}")
                logger.info(f"Source: {source}")
                logger.info(f"Timestamp: {timestamp}")
                
                if raw_data:
                    logger.info("")
                    logger.info("Raw Data:")
                    try:
                        # Try to parse as JSON
                        parsed = json.loads(raw_data)
                        for key, value in parsed.items():
                            logger.info(f"   {key}: {value}")
                    except:
                        # Show as string
                        logger.info(f"   {raw_data[:200]}")
                
                logger.info("")
        else:
            logger.info("⚠️  No orders found in the specified time range")
            logger.info("")
            logger.info("Possible reasons:")
            logger.info("  • Bot is not running")
            logger.info("  • No large orders detected yet")
            logger.info("  • Market is closed")
            logger.info("  • Threshold too high")
            logger.info("")
        
        # Statistics
        if recent_count > 0:
            cursor.execute("""
                SELECT 
                    SUM(order_size_usd) as total_value,
                    AVG(order_size_usd) as avg_value,
                    MIN(order_size_usd) as min_value,
                    MAX(order_size_usd) as max_value
                FROM order_flow
                WHERE timestamp >= %s AND order_size_usd IS NOT NULL
            """, (time_threshold,))
            
            stats = cursor.fetchone()
            if stats and stats[0]:
                logger.info("=" * 100)
                logger.info("📊 STATISTICS")
                logger.info("=" * 100)
                logger.info(f"   Total Value: ${stats[0]:,.2f}")
                logger.info(f"   Average Value: ${stats[1]:,.2f}")
                logger.info(f"   Min Value: ${stats[2]:,.2f}")
                logger.info(f"   Max Value: ${stats[3]:,.2f}")
                logger.info("")
        
        cursor.close()
        
        logger.info("=" * 100)
        if recent_count > 0:
            logger.info("✅ Database is being populated correctly!")
        else:
            logger.info("⚠️  No recent entries found - check if bot is running")
        logger.info("=" * 100)
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking database: {e}", exc_info=True)
        if db.conn:
            db.conn.rollback()
        return False
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check orders database')
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours to look back (default: 24)'
    )
    parser.add_argument(
        '--recent',
        action='store_true',
        help='Check last hour only'
    )
    
    args = parser.parse_args()
    
    success = check_database(hours=args.hours, recent_only=args.recent)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())


