"""
Fetch Orders - Display in Log Format
====================================

Fetches orders from database and displays them in the same format
as the bot logs them.

Usage:
    python3 fetch_orders.py                    # Last 50 orders
    python3 fetch_orders.py --hours 1           # Last hour
    python3 fetch_orders.py --limit 100         # Top 100 orders
"""
import os
import sys
import logging
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Configure logging to match bot format
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


def fetch_orders(hours: int = 24, limit: int = 50, order_type_filter: str = None):
    """Fetch orders from database"""
    if not DB_AVAILABLE:
        logger.error("Database module not available")
        return []
    
    db = get_db()
    
    if not db.connect():
        logger.error("Failed to connect to database")
        return []
    
    try:
        cursor = db.conn.cursor()
        
        # Calculate time threshold
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Build query
        query = """
            SELECT 
                id, ticker, order_type, order_size_usd, price, timestamp, 
                source, raw_data, display_ticker, instrument, order_side
            FROM order_flow
            WHERE timestamp >= %s
        """
        params = [time_threshold]
        
        # Add order type filter if specified
        if order_type_filter:
            query += " AND order_type LIKE %s"
            params.append(f"%{order_type_filter}%")
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            order = {
                'id': row[0],
                'symbol': row[1] or row[8] or 'N/A',
                'order_type': row[2] or 'N/A',
                'order_size_usd': float(row[3]) if row[3] else 0,
                'price': float(row[4]) if row[4] else None,
                'timestamp': row[5],
                'source': row[6] or 'N/A',
                'raw_data': row[7],
                'instrument': row[9] or 'equity',
                'order_side': row[10] or 'N/A',
            }
            
            # Parse raw_data if available
            if order['raw_data']:
                try:
                    parsed = json.loads(order['raw_data'])
                    order.update(parsed)
                except:
                    pass
            
            orders.append(order)
        
        cursor.close()
        return orders
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
        if db.conn:
            db.conn.rollback()
        return []
    finally:
        db.close()


def display_orders_log_format(orders: list):
    """Display orders in the same format as bot logs"""
    if not orders:
        logger.info("")
        logger.info("⚠️  No orders found")
        return
    
    logger.info("")
    logger.info("=" * 100)
    logger.info(f"📋 FETCHED {len(orders)} ORDER(S)")
    logger.info("=" * 100)
    logger.info("")
    
    # Display in log format (same as bot)
    for order in orders:
        symbol = order.get('symbol', 'N/A')
        order_type = order.get('order_type', 'N/A')
        order_value = order.get('order_size_usd', 0)
        price = order.get('price')
        timestamp = order.get('timestamp')
        instrument = order.get('instrument', 'equity')
        
        # Determine if it's an order or trade
        is_order = 'order' in order_type.lower()
        is_trade = 'trade' in order_type.lower()
        
        # Format timestamp
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                timestamp_str = str(timestamp)[:19]
        else:
            timestamp_str = str(timestamp)[:19]
        
        # Display based on type
        if is_order:
            # Order format (same as bot logs)
            order_side = order.get('order_side', 'UNKNOWN')
            order_size = order.get('order_size_shares', 0)
            
            logger.info(
                f"📋 Large {order_side} order detected: {symbol} | "
                f"Value: ${order_value:,.2f} | "
                f"Size: {order_size:,} shares @ ${price:.2f} | "
                f"Instrument: {instrument}"
            )
        elif is_trade:
            # Trade format (same as bot logs)
            entry_price = order.get('entry_price', price)
            exit_price = order.get('exit_price', price)
            volume = order.get('volume', 0)
            
            if entry_price and exit_price and entry_price != exit_price:
                logger.info(
                    f"💰 Large trade detected: {symbol} | "
                    f"Value: ${order_value:,.2f} | "
                    f"Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f} | "
                    f"Vol: {volume:,}"
                )
            else:
                logger.info(
                    f"💰 Large trade detected: {symbol} | "
                    f"Value: ${order_value:,.2f} | "
                    f"Price: ${price:.2f} | "
                    f"Vol: {volume:,}"
                )
        else:
            # Generic format
            logger.info(
                f"📊 {order_type}: {symbol} | "
                f"Value: ${order_value:,.2f} | "
                f"Price: ${price:.2f if price else 'N/A'}"
            )
        
        logger.info(f"   Timestamp: {timestamp_str}")
        logger.info("")
    
    # Summary
    logger.info("=" * 100)
    
    # Statistics
    total_value = sum(o.get('order_size_usd', 0) for o in orders)
    buy_orders = [o for o in orders if 'buy' in o.get('order_type', '').lower() or o.get('order_side', '').upper() == 'BUY']
    sell_orders = [o for o in orders if 'sell' in o.get('order_type', '').lower() or o.get('order_side', '').upper() == 'SELL']
    trades = [o for o in orders if 'trade' in o.get('order_type', '').lower()]
    
    logger.info(f"📊 Summary:")
    logger.info(f"   Total orders: {len(orders)}")
    logger.info(f"   Buy orders: {len(buy_orders)}")
    logger.info(f"   Sell orders: {len(sell_orders)}")
    logger.info(f"   Trades: {len(trades)}")
    logger.info(f"   Total value: ${total_value:,.2f}")
    logger.info("")
    
    # Top symbols
    symbol_counts = {}
    for order in orders:
        symbol = order.get('symbol', 'N/A')
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
    
    if symbol_counts:
        logger.info("📈 Top symbols:")
        sorted_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)
        for symbol, count in sorted_symbols[:10]:
            logger.info(f"   {symbol}: {count} order(s)")
        logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch orders from database and display in log format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_orders.py                    # Last 50 orders (24 hours)
  python3 fetch_orders.py --hours 1          # Last hour
  python3 fetch_orders.py --limit 100        # Top 100 orders
  python3 fetch_orders.py --type order       # Only orders (not trades)
  python3 fetch_orders.py --type trade       # Only trades
        """
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours to look back (default: 24)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Maximum number of orders to fetch (default: 50)'
    )
    parser.add_argument(
        '--type',
        choices=['order', 'trade'],
        help='Filter by type: order or trade'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 100)
    logger.info("🔍 FETCHING ORDERS FROM DATABASE")
    logger.info("=" * 100)
    logger.info(f"📋 Configuration:")
    logger.info(f"   Time range: Last {args.hours} hour(s)")
    logger.info(f"   Limit: {args.limit} orders")
    if args.type:
        logger.info(f"   Filter: {args.type} only")
    logger.info("")
    
    orders = fetch_orders(
        hours=args.hours,
        limit=args.limit,
        order_type_filter=args.type
    )
    
    display_orders_log_format(orders)
    
    if orders:
        logger.info("✅ Fetch completed successfully")
    else:
        logger.warning("⚠️  No orders found")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


