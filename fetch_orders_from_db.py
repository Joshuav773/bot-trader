"""
Fetch Last N Individual Orders from Database
============================================

Fetches INDIVIDUAL orders from your database (order_flow table).
EACH LINE = ONE SINGLE ORDER (not aggregated).

These are individual orders your bot detected and saved.
Shows: Symbol, Order Type (BUY/SELL), Size, Price, Timestamp, PUT/CALL (if options)

Usage:
    python3 fetch_orders_from_db.py AAPL 30
    python3 fetch_orders_from_db.py TSLA 50
    python3 fetch_orders_from_db.py AAPL 30 --email
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
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.error("Database module not available")

try:
    from notifications import get_notification_service
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False


def fetch_orders_from_db(symbol: str, limit: int = 30):
    """Fetch orders from database"""
    if not DB_AVAILABLE:
        logger.error("Database not available")
        return []
    
    db = get_db()
    if not db.connect():
        logger.error("Failed to connect to database")
        return []
    
    orders = []
    
    try:
        cursor = db.conn.cursor(cursor_factory=RealDictCursor)
        
        # Query order_flow table for the symbol
        query = """
            SELECT * FROM order_flow 
            WHERE (ticker = %s OR display_ticker = %s)
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        
        cursor.execute(query, (symbol.upper(), symbol.upper(), limit))
        rows = cursor.fetchall()
        
        for row in rows:
            # Parse raw_data if available
            raw_data = row.get('raw_data', '')
            if raw_data and isinstance(raw_data, str):
                try:
                    raw_data = json.loads(raw_data)
                except:
                    pass
            
            # Determine option type
            option_type = row.get('option_type')
            if not option_type and raw_data:
                option_type = raw_data.get('option_type')
            
            # Get order type
            order_type = row.get('order_type', 'UNKNOWN')
            order_side = row.get('order_side', 'UNKNOWN')
            
            # Determine if PUT or CALL
            if option_type:
                if 'PUT' in str(option_type).upper() or 'P' in str(option_type).upper():
                    option_type = 'PUT'
                elif 'CALL' in str(option_type).upper() or 'C' in str(option_type).upper():
                    option_type = 'CALL'
            
            order_data = {
                'symbol': row.get('ticker', row.get('display_ticker', symbol.upper())),
                'timestamp': row.get('timestamp'),
                'order_side': order_side,
                'order_type': order_type,
                'size': row.get('size', row.get('order_size_shares', 0)),
                'price': float(row.get('price', 0)),
                'value': float(row.get('order_size_usd', 0)),
                'instrument': row.get('instrument', 'equity'),
                'option_type': option_type,
                'contracts': row.get('contracts'),
                'option_strike': row.get('option_strike'),
                'option_expiration': row.get('option_expiration'),
            }
            
            orders.append(order_data)
        
        cursor.close()
        return orders
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
        return []
    finally:
        db.close()


def display_orders(orders: list, symbol: str):
    """Display orders in formatted table"""
    if not orders:
        logger.info("")
        logger.info("=" * 120)
        logger.info("❌ NO ORDERS FOUND IN DATABASE")
        logger.info("=" * 120)
        logger.info("")
        logger.info("Possible reasons:")
        logger.info("  • Bot hasn't detected any large orders for this symbol yet")
        logger.info("  • Orders are below the $50k threshold")
        logger.info("  • Bot is not running or hasn't saved orders yet")
        logger.info("")
        logger.info("💡 These are orders that your bot has already detected and saved")
        return
    
    logger.info("")
    logger.info("=" * 120)
    logger.info(f"📊 LAST {len(orders)} ORDERS FROM DATABASE - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("These are orders that your bot has ALREADY detected and saved (no API call needed)")
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<22} {'Type':<12} {'Side':<6} {'Size':<12} {'Price':<12} {'Value (USD)':<15} {'Option':<10}")
    logger.info("-" * 120)
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        
        # Format timestamp
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, str):
            try:
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                timestamp_str = str(timestamp)[:19]
        else:
            timestamp_str = str(timestamp)[:19] if timestamp else 'N/A'
        
        order_type = order.get('order_type', 'UNKNOWN')
        side = order.get('order_side', 'UNKNOWN')
        size = order.get('size', 0)
        price = order.get('price', 0)
        value = order.get('value', 0)
        option_type = order.get('option_type')
        
        # Format order type
        type_str = order_type
        if 'BUY_ORDER' in order_type:
            type_str = 'BUY ORDER'
        elif 'SELL_ORDER' in order_type:
            type_str = 'SELL ORDER'
        elif 'large_trade' in order_type.lower():
            type_str = 'TRADE'
        
        option_str = option_type if option_type else '-'
        
        print(f"{i:2d}.  {timestamp_str:<22} {type_str:<12} {side:<6} {size:>10,}  ${price:>10.4f}  ${value:>13,.2f}  {option_str:<10}")
    
    logger.info("-" * 120)
    
    # Summary
    total_value = sum(o.get('value', 0) for o in orders)
    total_size = sum(o.get('size', 0) for o in orders)
    buy_orders = [o for o in orders if 'BUY' in o.get('order_side', '').upper() or 'BUY' in o.get('order_type', '').upper()]
    sell_orders = [o for o in orders if 'SELL' in o.get('order_side', '').upper() or 'SELL' in o.get('order_type', '').upper()]
    option_orders = [o for o in orders if o.get('option_type')]
    stock_orders = [o for o in orders if not o.get('option_type')]
    prices = [o.get('price', 0) for o in orders if o.get('price', 0) > 0]
    
    logger.info("")
    logger.info("📈 Summary:")
    logger.info(f"   Total orders: {len(orders)}")
    logger.info(f"   BUY orders: {len(buy_orders)}")
    logger.info(f"   SELL orders: {len(sell_orders)}")
    logger.info(f"   Stock orders: {len(stock_orders)}")
    logger.info(f"   Option orders: {len(option_orders)}")
    logger.info(f"   Total size: {total_size:,} shares/contracts")
    logger.info(f"   Total value: ${total_value:,.2f}")
    if prices:
        logger.info(f"   Price range: ${min(prices):.4f} - ${max(prices):.4f}")
    logger.info("")
    logger.info("=" * 120)
    logger.info("✅ Data from your database (orders detected by your bot)")
    logger.info("=" * 120)
    logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch last N orders from database (already logged by bot)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_orders_from_db.py AAPL 30
  python3 fetch_orders_from_db.py TSLA 50
        """
    )
    parser.add_argument(
        'symbol',
        help='Stock symbol (e.g., AAPL, TSLA, NVDA)'
    )
    parser.add_argument(
        'limit',
        type=int,
        nargs='?',
        default=30,
        help='Number of orders to fetch (default: 30)'
    )
    
    args = parser.parse_args()
    
    if not DB_AVAILABLE:
        logger.error("Database module not available")
        return 1
    
    symbol = args.symbol.upper()
    limit = args.limit
    
    logger.info("=" * 120)
    logger.info(f"🔍 FETCHING LAST {limit} ORDERS FROM DATABASE - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("This fetches orders that your bot has ALREADY detected and saved")
    logger.info("No API calls, no waiting - instant results from your database")
    logger.info("")
    
    orders = fetch_orders_from_db(symbol, limit=limit)
    display_orders(orders, symbol)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

