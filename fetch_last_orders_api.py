"""
Fetch Last N Orders from Schwab REST API
=========================================

Fetches the last N orders from Schwab REST API - NO WAITING, instant results.

IMPORTANT: Schwab REST API does NOT provide individual order executions.
This script uses Price History API and formats each minute as an "order".

Usage:
    python3 fetch_last_orders_api.py AAPL 30
    python3 fetch_last_orders_api.py TSLA 50
"""
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from schwab.auth import client_from_token_file
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    logger.error("schwab-py not installed. Run: pip install schwab-py")

try:
    from notifications import get_notification_service
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False


def fetch_last_orders(client, symbol: str, limit: int = 30):
    """Fetch last N orders from Price History API"""
    try:
        # Get price history for last 24 hours (enough to get N minutes)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        # Try get_price_history_every_minute
        if hasattr(client, 'get_price_history_every_minute'):
            logger.info(f"   Using get_price_history_every_minute...")
            result = client.get_price_history_every_minute(
                symbol, 
                start_datetime=start_time, 
                end_datetime=end_time
            )
        elif hasattr(client, 'get_price_history'):
            logger.info(f"   Using get_price_history...")
            result = client.get_price_history(
                symbol,
                start_datetime=start_time,
                end_datetime=end_time
            )
        else:
            logger.error("   No price history method available")
            return []
        
        # Handle response
        if hasattr(result, 'json'):
            data = result.json()
        elif hasattr(result, 'status_code'):
            if result.status_code == 200:
                data = result.json()
            else:
                logger.error(f"   API returned status {result.status_code}")
                return []
        elif isinstance(result, dict):
            data = result
        else:
            logger.error("   Unexpected response format")
            return []
        
        # Extract candles
        candles = data.get('candles', data.get('data', data.get('priceHistory', [])))
        
        if not candles or not isinstance(candles, list):
            logger.error("   No data returned from API")
            return []
        
        logger.info(f"   ✅ Found {len(candles)} data points")
        
        # Get last N candles and format as orders
        orders = []
        for candle in candles[-limit:]:
            if not isinstance(candle, dict):
                continue
            
            # Extract data
            timestamp = candle.get('datetime', candle.get('time', candle.get('timestamp')))
            close_price = candle.get('close', candle.get('price', 0))
            volume = candle.get('volume', 0)
            open_price = candle.get('open', close_price)
            high = candle.get('high', close_price)
            low = candle.get('low', close_price)
            
            # Format timestamp
            if isinstance(timestamp, (int, float)):
                if timestamp > 1e10:
                    timestamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                else:
                    timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            # Determine side based on price movement
            if open_price and close_price:
                if close_price > open_price:
                    side = 'BUY'
                elif close_price < open_price:
                    side = 'SELL'
                else:
                    side = 'NEUTRAL'
            else:
                side = 'UNKNOWN'
            
            order = {
                'symbol': symbol.upper(),
                'timestamp': timestamp,
                'order_side': side,
                'size': int(volume) if volume else 0,
                'price': float(close_price) if close_price else 0.0,
                'value': float(close_price) * int(volume) if (close_price and volume) else 0.0,
                'open': float(open_price) if open_price else 0.0,
                'high': float(high) if high else 0.0,
                'low': float(low) if low else 0.0,
                'order_type': 'STOCK',
            }
            
            orders.append(order)
        
        return orders
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
        return []


def display_orders(orders: list, symbol: str):
    """Display orders in formatted table"""
    if not orders:
        logger.info("")
        logger.info("=" * 120)
        logger.info("❌ NO ORDERS FOUND")
        logger.info("=" * 120)
        return
    
    logger.info("")
    logger.info("=" * 120)
    logger.info(f"📊 LAST {len(orders)} ORDERS - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("⚠️  NOTE: Schwab REST API does NOT provide individual order executions")
    logger.info("   This shows minute-by-minute trading activity (closest available)")
    logger.info("   Each row = 1 minute of aggregated trades")
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<22} {'Side':<6} {'Size':<12} {'Price':<12} {'Value (USD)':<15} {'Type':<10}")
    logger.info("-" * 120)
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)[:19]
        
        side = order.get('order_side', 'UNKNOWN')
        size = order.get('size', 0)
        price = order.get('price', 0)
        value = order.get('value', 0)
        order_type = order.get('order_type', 'STOCK')
        
        print(f"{i:2d}.  {timestamp_str:<22} {side:<6} {size:>10,}  ${price:>10.4f}  ${value:>13,.2f}  {order_type:<10}")
    
    logger.info("-" * 120)
    
    # Summary
    total_value = sum(o.get('value', 0) for o in orders)
    total_size = sum(o.get('size', 0) for o in orders)
    buy_orders = [o for o in orders if o.get('order_side') == 'BUY']
    sell_orders = [o for o in orders if o.get('order_side') == 'SELL']
    prices = [o.get('price', 0) for o in orders if o.get('price', 0) > 0]
    
    logger.info("")
    logger.info("📈 Summary:")
    logger.info(f"   Total orders: {len(orders)}")
    logger.info(f"   BUY orders: {len(buy_orders)}")
    logger.info(f"   SELL orders: {len(sell_orders)}")
    logger.info(f"   Total size: {total_size:,} shares")
    logger.info(f"   Total value: ${total_value:,.2f}")
    if prices:
        logger.info(f"   Price range: ${min(prices):.4f} - ${max(prices):.4f}")
    logger.info("")
    logger.info("=" * 120)
    logger.info("✅ Data from Schwab REST API (Price History)")
    logger.info("=" * 120)
    logger.info("")
    
    return orders


def format_orders_email(orders: list, symbol: str) -> tuple:
    """Format orders data as email"""
    if not orders:
        subject = f"📊 Orders Report: {symbol} - No Data"
        body = f"No orders found for {symbol}."
        return subject, body, body
    
    total_value = sum(o.get('value', 0) for o in orders)
    total_size = sum(o.get('size', 0) for o in orders)
    buy_orders = [o for o in orders if o.get('order_side') == 'BUY']
    sell_orders = [o for o in orders if o.get('order_side') == 'SELL']
    prices = [o.get('price', 0) for o in orders if o.get('price', 0) > 0]
    
    subject = f"📊 Last {len(orders)} Orders: {symbol} - ${total_value:,.0f} Total Value"
    
    # HTML body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #4CAF50; color: white; padding: 15px; }}
            .content {{ padding: 20px; }}
            .table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .table th {{ background-color: #f2f2f2; }}
            .stats {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; }}
            .note {{ background-color: #fff3cd; padding: 10px; margin: 20px 0; border-left: 4px solid #ffc107; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📊 Last {len(orders)} Orders - {symbol}</h2>
        </div>
        <div class="content">
            <div class="note">
                <strong>Note:</strong> Schwab REST API does not provide individual order executions.
                This shows minute-by-minute trading activity (closest available).
            </div>
            <div class="stats">
                <h3>Summary</h3>
                <p><strong>Total Orders:</strong> {len(orders)}</p>
                <p><strong>BUY Orders:</strong> {len(buy_orders)}</p>
                <p><strong>SELL Orders:</strong> {len(sell_orders)}</p>
                <p><strong>Total Value:</strong> ${total_value:,.2f}</p>
                <p><strong>Total Size:</strong> {total_size:,} shares</p>
                {f'<p><strong>Price Range:</strong> ${min(prices):.2f} - ${max(prices):.2f}</p>' if prices else ''}
            </div>
            
            <table class="table">
                <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Side</th>
                    <th>Size</th>
                    <th>Price</th>
                    <th>Value (USD)</th>
                    <th>Type</th>
                </tr>
    """
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)[:19]
        
        side = order.get('order_side', 'UNKNOWN')
        size = order.get('size', 0)
        price = order.get('price', 0)
        value = order.get('value', 0)
        order_type = order.get('order_type', 'STOCK')
        
        html_body += f"""
                <tr>
                    <td>{i}</td>
                    <td>{timestamp_str}</td>
                    <td>{side}</td>
                    <td>{size:,}</td>
                    <td>${price:.4f}</td>
                    <td>${value:,.2f}</td>
                    <td>{order_type}</td>
                </tr>
        """
    
    html_body += """
            </table>
            <p><em>Data from Schwab REST API (Price History)</em></p>
        </div>
    </body>
    </html>
    """
    
    # Plain text body
    text_body = f"Last {len(orders)} Orders for {symbol}\n\n"
    text_body += f"Total Value: ${total_value:,.2f}\n"
    text_body += f"Total Size: {total_size:,} shares\n"
    text_body += f"BUY Orders: {len(buy_orders)}\n"
    text_body += f"SELL Orders: {len(sell_orders)}\n"
    if prices:
        text_body += f"Price Range: ${min(prices):.2f} - ${max(prices):.2f}\n"
    text_body += "\n"
    text_body += "Note: Schwab REST API does not provide individual order executions.\n"
    text_body += "This shows minute-by-minute trading activity.\n\n"
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)[:19]
        
        side = order.get('order_side', 'UNKNOWN')
        size = order.get('size', 0)
        price = order.get('price', 0)
        value = order.get('value', 0)
        
        text_body += f"{i}. {timestamp_str} | {side} | {size:,} @ ${price:.4f} = ${value:,.2f}\n"
    
    text_body += "\nData from Schwab REST API (Price History)"
    
    return subject, text_body, html_body


def send_email_results(orders: list, symbol: str):
    """Send email with order results"""
    if not NOTIFICATIONS_AVAILABLE:
        logger.warning("⚠️  Email notifications not available")
        return False
    
    notification_service = get_notification_service()
    
    if not notification_service.gmail_user or not notification_service.gmail_password:
        logger.warning("⚠️  Gmail credentials not configured")
        return False
    
    recipients = notification_service.get_alert_recipients()
    if not recipients:
        logger.warning("⚠️  No email recipients found in database")
        return False
    
    subject, text_body, html_body = format_orders_email(orders, symbol)
    
    sent = 0
    for recipient in recipients:
        email = recipient.get('email')
        if email:
            if notification_service.send_email(email, subject, text_body, html_body):
                sent += 1
                logger.info(f"📧 Email sent to {email}")
    
    if sent > 0:
        logger.info(f"✅ Sent email report to {sent} recipient(s)")
        return True
    
    return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch last N orders from Schwab REST API (instant, no waiting)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_last_orders_api.py AAPL 30
  python3 fetch_last_orders_api.py TSLA 50
  python3 fetch_last_orders_api.py AAPL 30 --email

IMPORTANT: Schwab REST API does NOT provide individual order executions.
           This uses Price History API (minute-by-minute data).
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
    parser.add_argument(
        '--email',
        action='store_true',
        help='Send results via email to alert recipients'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    symbol = args.symbol.upper()
    limit = args.limit
    
    logger.info("=" * 120)
    logger.info(f"🔍 FETCHING LAST {limit} ORDERS FROM API - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("⚠️  LIMITATION: Schwab REST API does NOT provide individual order executions")
    logger.info("   This script uses Price History API (minute-by-minute aggregated data)")
    logger.info("   Each 'order' = 1 minute of trading activity")
    logger.info("   NO WAITING - instant results from REST API")
    logger.info("")
    
    try:
        app_key = os.getenv("SCHWAB_APP_KEY")
        app_secret = os.getenv("SCHWAB_APP_SECRET")
        
        if not app_key or not app_secret:
            logger.error("SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in .env")
            return 1
        
        token_path = Path("token.json")
        if not token_path.exists():
            logger.error("token.json not found. Run schwab_streamer.py first to authenticate.")
            return 1
        
        logger.info("🔐 Authenticating...")
        client = client_from_token_file(
            token_path=str(token_path),
            app_secret=app_secret,
            api_key=app_key,
        )
        logger.info("✅ Authenticated")
        logger.info("")
        
        logger.info(f"📡 Fetching last {limit} orders for {symbol}...")
        orders = fetch_last_orders(client, symbol, limit=limit)
        
        if orders:
            display_orders(orders, symbol)
            
            # Send email if requested
            if args.email:
                logger.info("")
                logger.info("📧 Sending email report...")
                send_email_results(orders, symbol)
        else:
            logger.error("❌ Could not fetch orders from API")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

