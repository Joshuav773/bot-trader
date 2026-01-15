"""
Get Last 50 Individual Orders/Trades from Schwab Streaming API
================================================================

Fetches individual trade executions (not aggregated) directly from Schwab Streaming API.
Each trade represents an actual order execution with price, volume, and timestamp.

Usage:
    python3 get_orders_api.py NVDA
    python3 get_orders_api.py AAPL --limit 100
    python3 get_orders_api.py TSLA --email
"""
import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import deque
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
    from schwab.streaming import StreamClient
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    logger.error("schwab-py not installed. Run: pip install schwab-py")

try:
    from notifications import get_notification_service
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False


class IndividualTradeCollector:
    """Collect individual trade executions from streaming API"""
    
    def __init__(self, symbol: str, limit: int = 50):
        self.symbol = symbol.upper()
        self.limit = limit
        self.trades = deque(maxlen=limit)
        self.stream_client = None
        self.client = None
        self.running = False
        self.last_volume = None
        self.last_price = None
        
    def process_quote(self, msg):
        """Process incoming quote data and extract individual trades"""
        try:
            if isinstance(msg, dict):
                service = msg.get('service', '')
                if service == 'LEVELONE_EQUITIES':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('1', ''))
                            
                            if symbol != self.symbol:
                                continue
                            
                            # Extract trade data
                            last_price = item.get('4', None)  # Last trade price
                            volume = item.get('8', None)       # Total volume
                            bid = item.get('2', None)
                            ask = item.get('3', None)
                            bid_size = item.get('5', None)
                            ask_size = item.get('6', None)
                            timestamp = datetime.now(timezone.utc)
                            
                            if last_price is not None:
                                last_price = float(last_price)
                                volume = int(volume) if volume else 0
                                
                                # Detect individual trade execution
                                # A trade occurs when:
                                # 1. Price changes (new execution)
                                # 2. Volume increases (new execution)
                                
                                is_new_trade = False
                                trade_volume = 0
                                
                                if self.last_price is None:
                                    # First quote - initialize
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    return
                                
                                # Check if price changed (new trade execution)
                                if last_price != self.last_price:
                                    is_new_trade = True
                                    # Estimate trade volume from volume delta
                                    if volume > self.last_volume:
                                        trade_volume = volume - self.last_volume
                                    else:
                                        trade_volume = 1  # Minimum 1 share
                                
                                # If price didn't change but volume did, might be multiple trades at same price
                                elif volume > self.last_volume:
                                    is_new_trade = True
                                    trade_volume = volume - self.last_volume
                                
                                if is_new_trade and trade_volume > 0:
                                    trade = {
                                        'symbol': symbol,
                                        'timestamp': timestamp,
                                        'price': last_price,
                                        'volume': trade_volume,
                                        'total_volume': volume,
                                        'bid': float(bid) if bid else None,
                                        'ask': float(ask) if ask else None,
                                        'bid_size': int(bid_size) if bid_size else None,
                                        'ask_size': int(ask_size) if ask_size else None,
                                        'trade_value': last_price * trade_volume,
                                    }
                                    
                                    self.trades.append(trade)
                                    
                                    # Update tracking
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    
                                    # Stop if we have enough trades
                                    if len(self.trades) >= self.limit:
                                        self.running = False
                                    
        except Exception as e:
            logger.debug(f"Error processing quote: {e}")
    
    async def collect_trades(self, client, timeout_minutes: int = 5):
        """Collect individual trades via streaming API"""
        self.client = client
        
        try:
            # Initialize stream client
            self.stream_client = StreamClient(
                client=client,
                account_id=None,
                enforce_enums=False,
            )
            
            # Register handler
            self.stream_client.add_level_one_equity_handler(self.process_quote)
            
            logger.info("🔐 Logging into streaming API...")
            await self.stream_client.login()
            
            logger.info(f"📡 Subscribing to {self.symbol}...")
            await self.stream_client.level_one_equity_subs(
                symbols=[self.symbol],
                fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
            )
            
            logger.info(f"✅ Streaming started - collecting individual trades...")
            logger.info(f"   Target: {self.limit} individual trades")
            logger.info(f"   Timeout: {timeout_minutes} minutes")
            logger.info("")
            
            # Stream until we have enough trades or timeout
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(minutes=timeout_minutes)
            self.running = True
            
            while self.running and datetime.now(timezone.utc) < end_time:
                try:
                    await self.stream_client.handle_message()
                    await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning
                except Exception as e:
                    error_type = type(e).__name__
                    if "ConnectionClosed" in error_type or "IncompleteRead" in error_type:
                        logger.warning(f"⚠️  Connection lost: {error_type}")
                        break
                    else:
                        logger.debug(f"Streaming error: {e}")
                        await asyncio.sleep(1)
            
            # Cleanup
            if self.stream_client:
                try:
                    await self.stream_client.logout()
                except:
                    pass
            
            return list(self.trades)
            
        except Exception as e:
            logger.error(f"Error collecting trades: {e}", exc_info=True)
            return list(self.trades)


def get_quotes_batch(client, symbols: list):
    """Get quotes for multiple symbols"""
    try:
        methods_to_try = [
            'get_quotes',
            'get_quote',
        ]
        
        for method_name in methods_to_try:
            if hasattr(client, method_name):
                method = getattr(client, method_name)
                try:
                    # Try with list
                    result = method(symbols)
                    
                    if hasattr(result, 'status_code'):
                        if result.status_code == 200:
                            data = result.json()
                            # Handle different response formats
                            if isinstance(data, dict):
                                if symbol in data:
                                    return data[symbol]
                                return data
                            elif isinstance(data, list):
                                return data
                        continue
                    elif isinstance(result, dict):
                        return result
                    elif isinstance(result, list):
                        return result
                except TypeError:
                    # Try with single symbol (call multiple times)
                    quotes = {}
                    for sym in symbols:
                        quote = get_quote(client, sym)
                        if quote:
                            quotes[sym] = quote
                    return quotes
                except Exception as e:
                    logger.debug(f"{method_name} failed: {e}")
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting quotes: {e}")
        return None


def format_trades_data(trades: list):
    """Format collected trades for display"""
    orders = []
    
    for trade in trades:
        order = {
            'symbol': trade.get('symbol'),
            'timestamp': trade.get('timestamp'),
            'price': trade.get('price'),
            'volume': trade.get('volume', 0),
            'total_volume': trade.get('total_volume', 0),
            'bid': trade.get('bid'),
            'ask': trade.get('ask'),
            'bid_size': trade.get('bid_size'),
            'ask_size': trade.get('ask_size'),
            'trade_value': trade.get('trade_value', 0),
        }
        orders.append(order)
    
    return orders


def display_orders(orders: list, symbol: str):
    """Display individual orders/trades in formatted table"""
    if not orders:
        logger.info(f"\n❌ No individual trades found for {symbol}")
        logger.info("")
        logger.info("Possible reasons:")
        logger.info("  • Market is closed")
        logger.info("  • Symbol not trading actively")
        logger.info("  • Connection timeout")
        return
    
    logger.info("")
    logger.info("=" * 100)
    logger.info(f"📊 LAST {len(orders)} INDIVIDUAL TRADES - {symbol}")
    logger.info("=" * 100)
    logger.info("")
    logger.info("Note: Each row represents an individual trade execution (not aggregated)")
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<20} {'Price':<12} {'Volume':<15} {'Value (USD)':<15} {'Bid':<10} {'Ask':<10}")
    logger.info("-" * 100)
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        
        # Format timestamp
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elif isinstance(timestamp, (int, float)):
            if timestamp > 1e10:
                timestamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            except:
                timestamp_str = str(timestamp)[:23]
        else:
            timestamp_str = str(timestamp)[:23]
        
        price = order.get('price', 0)
        volume = order.get('volume', 0)
        trade_value = order.get('trade_value', price * volume if price and volume else 0)
        bid = order.get('bid')
        ask = order.get('ask')
        
        bid_str = f"${bid:.2f}" if bid else "N/A"
        ask_str = f"${ask:.2f}" if ask else "N/A"
        
        print(f"{i:2d}.  {timestamp_str:<20} ${price:>10.4f}  {volume:>12,}  ${trade_value:>13,.2f}  {bid_str:<10} {ask_str:<10}")
    
    logger.info("-" * 100)
    
    # Statistics
    if orders:
        prices = [o.get('price', 0) for o in orders if o.get('price')]
        volumes = [o.get('volume', 0) for o in orders if o.get('volume')]
        total_value = sum(o.get('trade_value', 0) for o in orders)
        
        logger.info("")
        logger.info(f"📈 Statistics:")
        if prices:
            logger.info(f"   First price: ${prices[0]:.4f}")
            logger.info(f"   Last price:  ${prices[-1]:.4f}")
            logger.info(f"   High:        ${max(prices):.4f}")
            logger.info(f"   Low:         ${min(prices):.4f}")
        if volumes:
            logger.info(f"   Total shares traded: {sum(volumes):,}")
            logger.info(f"   Average trade size: {sum(volumes) / len(volumes):,.0f} shares")
        logger.info(f"   Total value: ${total_value:,.2f}")
        logger.info("")
    
    logger.info("✅ Individual trades from Schwab Streaming API")
    logger.info("")
    
    return orders


def format_orders_email(orders: list, symbol: str) -> tuple:
    """Format individual orders data as email"""
    if not orders:
        subject = f"📊 Individual Trades Report: {symbol} - No Data"
        body = f"No individual trades found for {symbol}."
        return subject, body, body
    
    total_value = sum(o.get('trade_value', 0) for o in orders)
    prices = [o.get('price', 0) for o in orders if o.get('price')]
    
    subject = f"📊 Last {len(orders)} Individual Trades: {symbol} - ${total_value:,.0f} Total Value"
    
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
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📊 Last {len(orders)} Individual Trades - {symbol}</h2>
        </div>
        <div class="content">
            <p><em>Each row represents an individual trade execution (not aggregated)</em></p>
            <div class="stats">
                <h3>Summary</h3>
                <p><strong>Total Individual Trades:</strong> {len(orders)}</p>
                <p><strong>Total Value:</strong> ${total_value:,.2f}</p>
                {f'<p><strong>Price Range:</strong> ${min(prices):.2f} - ${max(prices):.2f}</p>' if prices else ''}
            </div>
            
            <table class="table">
                <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Price</th>
                    <th>Volume</th>
                    <th>Value (USD)</th>
                    <th>Bid</th>
                    <th>Ask</th>
                </tr>
    """
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elif isinstance(timestamp, (int, float)):
            if timestamp > 1e10:
                timestamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            except:
                timestamp_str = str(timestamp)[:23]
        else:
            timestamp_str = str(timestamp)[:23]
        
        price = order.get('price', 0)
        volume = order.get('volume', 0)
        trade_value = order.get('trade_value', 0)
        bid = order.get('bid')
        ask = order.get('ask')
        
        bid_str = f"${bid:.2f}" if bid else "N/A"
        ask_str = f"${ask:.2f}" if ask else "N/A"
        
        html_body += f"""
                <tr>
                    <td>{i}</td>
                    <td>{timestamp_str}</td>
                    <td>${price:.4f}</td>
                    <td>{volume:,}</td>
                    <td>${trade_value:,.2f}</td>
                    <td>{bid_str}</td>
                    <td>{ask_str}</td>
                </tr>
        """
    
    html_body += """
            </table>
            <p><em>Data from Schwab Streaming API (Individual Trade Executions)</em></p>
        </div>
    </body>
    </html>
    """
    
    # Plain text body
    text_body = f"Last {len(orders)} Individual Trades for {symbol}\n\n"
    text_body += f"Total Value: ${total_value:,.2f}\n"
    if prices:
        text_body += f"Price Range: ${min(prices):.2f} - ${max(prices):.2f}\n"
    text_body += "\n"
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elif isinstance(timestamp, (int, float)):
            if timestamp > 1e10:
                timestamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            except:
                timestamp_str = str(timestamp)[:23]
        else:
            timestamp_str = str(timestamp)[:23]
        
        price = order.get('price', 0)
        volume = order.get('volume', 0)
        trade_value = order.get('trade_value', 0)
        
        text_body += f"{i}. {timestamp_str} | ${price:.4f} | Vol: {volume:,} | Value: ${trade_value:,.2f}\n"
    
    text_body += "\nData from Schwab Streaming API (Individual Trade Executions)"
    
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
        description='Get order data from Schwab API for a symbol',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 get_orders_api.py NVDA
  python3 get_orders_api.py AAPL
  python3 get_orders_api.py TSLA --email
        """
    )
    parser.add_argument(
        'symbol',
        help='Stock symbol (e.g., NVDA, AAPL, TSLA)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Number of individual trades to collect (default: 50)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=5,
        help='Timeout in minutes for collecting trades (default: 5)'
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
    
    logger.info("=" * 100)
    logger.info(f"🔍 FETCHING INDIVIDUAL TRADES FROM SCHWAB STREAMING API - {symbol}")
    logger.info("=" * 100)
    logger.info("")
    logger.info("Note: This collects individual trade executions (not aggregated data)")
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
        
        # Collect individual trades via streaming API
        logger.info(f"📡 Collecting {args.limit} individual trades for {symbol}...")
        logger.info(f"   This may take up to {args.timeout} minutes")
        logger.info("")
        
        collector = IndividualTradeCollector(symbol, limit=args.limit)
        trades = asyncio.run(collector.collect_trades(client, timeout_minutes=args.timeout))
        
        if trades:
            logger.info("")
            logger.info(f"✅ Collected {len(trades)} individual trades")
            logger.info("")
            orders = format_trades_data(trades)
            display_orders(orders, symbol)
            
            # Send email if requested
            if args.email and orders:
                logger.info("")
                logger.info("📧 Sending email report...")
                send_email_results(orders, symbol)
        else:
            logger.warning("⚠️  No individual trades collected")
            logger.info("")
            logger.info("Possible reasons:")
            logger.info("  • Market is closed")
            logger.info("  • Symbol not trading actively")
            logger.info("  • Connection timeout")
            logger.info("  • Try increasing --timeout value")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
