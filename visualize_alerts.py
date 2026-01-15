"""
Visualize Alerts - Test Individual Trades Display
=================================================

Fetches the last 30 individual trades/orders from the database
and displays them in a clear format to visualize how alerts should look.

This is a TEST script to see individual trades and decide on alert formatting.

Usage:
    python3 visualize_alerts.py              # Last 30 orders
    python3 visualize_alerts.py --limit 50  # Last 50 orders
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


def fetch_last_orders(limit: int = 30):
    """Fetch last N individual orders/trades from database"""
    if not DB_AVAILABLE:
        logger.error("Database module not available")
        return []
    
    db = get_db()
    
    if not db.connect():
        logger.error("Failed to connect to database")
        return []
    
    try:
        cursor = db.conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch last N orders, most recent first
        query = """
            SELECT 
                id, ticker, order_type, order_size_usd, price, timestamp, 
                source, raw_data, display_ticker, instrument, order_side,
                size, option_type, contracts, option_strike, option_expiration
            FROM order_flow
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            order = dict(row)
            
            # Parse raw_data if it's JSON
            if order.get('raw_data'):
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


def format_timestamp(timestamp):
    """Format timestamp for display"""
    if isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
    elif isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return str(timestamp)[:19]
    else:
        return str(timestamp)[:19]


def visualize_alerts(orders: list):
    """Display orders in a clear format for alert visualization"""
    if not orders:
        logger.info("")
        logger.info("=" * 100)
        logger.info("⚠️  NO ORDERS FOUND")
        logger.info("=" * 100)
        logger.info("")
        logger.info("The database is empty. Run the bot to collect orders/trades first.")
        logger.info("")
        return
    
    logger.info("")
    logger.info("=" * 100)
    logger.info(f"📊 VISUALIZING LAST {len(orders)} INDIVIDUAL TRADES/ORDERS")
    logger.info("=" * 100)
    logger.info("")
    logger.info("This shows how alerts will look for individual trades/orders")
    logger.info("")
    logger.info("=" * 100)
    logger.info("")
    
    # Display each order/trade
    for i, order in enumerate(orders, 1):
        symbol = order.get('ticker') or order.get('display_ticker') or 'N/A'
        order_type = order.get('order_type', 'N/A')
        order_value = float(order.get('order_size_usd', 0) or 0)
        price = float(order.get('price', 0) or 0)
        timestamp = order.get('timestamp')
        instrument = order.get('instrument', 'equity')
        order_side = order.get('order_side', 'N/A')
        
        # Format timestamp
        timestamp_str = format_timestamp(timestamp)
        
        # Determine if it's an order or trade
        is_buy_order = 'buy' in order_type.lower() or order_side.upper() == 'BUY'
        is_sell_order = 'sell' in order_type.lower() or order_side.upper() == 'SELL'
        is_trade = 'trade' in order_type.lower()
        
        # Display header
        logger.info(f"┌{'─' * 98}┐")
        logger.info(f"│ #{i:2d} - {symbol:6s} │ {timestamp_str:<30} │")
        logger.info(f"├{'─' * 98}┤")
        
        # Display based on type
        if is_buy_order:
            # BUY ORDER
            order_size = order.get('order_size_shares') or order.get('size') or 0
            logger.info(f"│ 📋 TYPE: BUY ORDER")
            logger.info(f"│ 💰 VALUE: ${order_value:>15,.2f}")
            logger.info(f"│ 📊 SIZE:  {int(order_size):>15,} shares")
            logger.info(f"│ 💵 PRICE: ${price:>15,.2f}")
            logger.info(f"│ 📈 INSTRUMENT: {instrument}")
            
        elif is_sell_order:
            # SELL ORDER
            order_size = order.get('order_size_shares') or order.get('size') or 0
            logger.info(f"│ 📋 TYPE: SELL ORDER")
            logger.info(f"│ 💰 VALUE: ${order_value:>15,.2f}")
            logger.info(f"│ 📊 SIZE:  {int(order_size):>15,} shares")
            logger.info(f"│ 💵 PRICE: ${price:>15,.2f}")
            logger.info(f"│ 📈 INSTRUMENT: {instrument}")
            
        elif is_trade:
            # TRADE
            entry_price = order.get('entry_price', price)
            exit_price = order.get('exit_price', price)
            volume = order.get('volume', 0)
            price_change = order.get('price_change')
            price_change_pct = order.get('price_change_pct')
            
            logger.info(f"│ 💰 TYPE: TRADE EXECUTION")
            logger.info(f"│ 💵 VALUE: ${order_value:>15,.2f}")
            logger.info(f"│ 📊 VOLUME: {int(volume):>14,} shares")
            
            if entry_price and exit_price and entry_price != exit_price:
                logger.info(f"│ 📈 ENTRY: ${float(entry_price):>15,.2f}")
                logger.info(f"│ 📉 EXIT:  ${float(exit_price):>15,.2f}")
                if price_change:
                    change_str = f"${price_change:+.2f}"
                    if price_change_pct:
                        change_str += f" ({price_change_pct:+.2f}%)"
                    logger.info(f"│ 🔄 CHANGE: {change_str:>15}")
            else:
                logger.info(f"│ 💵 PRICE: ${price:>15,.2f}")
            
            logger.info(f"│ 📈 INSTRUMENT: {instrument}")
            
        else:
            # GENERIC
            logger.info(f"│ 📊 TYPE: {order_type}")
            logger.info(f"│ 💰 VALUE: ${order_value:>15,.2f}")
            logger.info(f"│ 💵 PRICE: ${price:>15,.2f}")
            logger.info(f"│ 📈 INSTRUMENT: {instrument}")
        
        # Options data if available
        if instrument == 'option':
            option_type = order.get('option_type', 'N/A')
            contracts = order.get('contracts', 0)
            strike = order.get('option_strike')
            expiration = order.get('option_expiration')
            
            logger.info(f"│ 🎯 OPTION TYPE: {option_type}")
            logger.info(f"│ 📊 CONTRACTS: {int(contracts):>13,}")
            if strike:
                logger.info(f"│ 💰 STRIKE: ${float(strike):>16,.2f}")
            if expiration:
                logger.info(f"│ 📅 EXPIRATION: {str(expiration):>13}")
        
        logger.info(f"└{'─' * 98}┘")
        logger.info("")
    
    # Summary
    logger.info("=" * 100)
    logger.info("📊 SUMMARY")
    logger.info("=" * 100)
    
    buy_orders = [o for o in orders if 'buy' in o.get('order_type', '').lower() or o.get('order_side', '').upper() == 'BUY']
    sell_orders = [o for o in orders if 'sell' in o.get('order_type', '').lower() or o.get('order_side', '').upper() == 'SELL']
    trades = [o for o in orders if 'trade' in o.get('order_type', '').lower()]
    
    total_value = sum(float(o.get('order_size_usd', 0) or 0) for o in orders)
    
    logger.info(f"   Total items: {len(orders)}")
    logger.info(f"   Buy orders: {len(buy_orders)}")
    logger.info(f"   Sell orders: {len(sell_orders)}")
    logger.info(f"   Trades: {len(trades)}")
    logger.info(f"   Total value: ${total_value:,.2f}")
    logger.info("")
    
    # Time range
    if orders:
        first_time = orders[-1].get('timestamp')
        last_time = orders[0].get('timestamp')
        if first_time and last_time:
            first_str = format_timestamp(first_time)
            last_str = format_timestamp(last_time)
            logger.info(f"   Time range: {first_str} → {last_str}")
            logger.info("")
    
    logger.info("=" * 100)
    logger.info("✅ Visualization complete")
    logger.info("")
    logger.info("💡 Use this format to design your alert notifications")
    logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Visualize last N individual trades/orders for alert formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 visualize_alerts.py              # Last 30 orders
  python3 visualize_alerts.py --limit 50  # Last 50 orders
  python3 visualize_alerts.py --limit 10  # Last 10 orders
        """
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=30,
        help='Number of orders to fetch and visualize (default: 30)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 100)
    logger.info("🔍 VISUALIZE ALERTS - TEST INDIVIDUAL TRADES")
    logger.info("=" * 100)
    logger.info("")
    logger.info(f"📋 Configuration:")
    logger.info(f"   Fetching last {args.limit} orders/trades from database")
    logger.info("")
    
    orders = fetch_last_orders(limit=args.limit)
    visualize_alerts(orders)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

