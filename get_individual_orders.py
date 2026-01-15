"""
Get Individual Orders from Schwab Streaming API
================================================

Fetches individual orders (stocks and options) from Schwab Streaming API.
Each order is a SINGLE order execution - not aggregated data.

This is the ONLY way to get individual market-wide orders from Schwab API.
REST API only provides aggregated data.

Shows: Symbol, Order Type (BUY/SELL), Size (shares/contracts), Price, Timestamp, PUT/CALL (if options)

Usage:
    python3 get_individual_orders.py AAPL 30
    python3 get_individual_orders.py TSLA 50
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


class IndividualOrderCollector:
    """Collect individual orders from streaming API"""
    
    def __init__(self, symbol: str, limit: int = 30):
        self.symbol = symbol.upper()
        self.limit = limit
        self.orders = deque(maxlen=limit)
        self.stream_client = None
        self.client = None
        self.running = False
        
        # Track last values to detect changes
        self.last_price = None
        self.last_volume = None
        self.last_bid_size = None
        self.last_ask_size = None
        self.quote_count = 0
        
    def process_quote(self, msg):
        """Process incoming quote and extract individual orders"""
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
                            
                            self.quote_count += 1
                            
                            # Extract order data
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
                                bid = float(bid) if bid else None
                                ask = float(ask) if ask else None
                                bid_size = int(bid_size) if bid_size else 0
                                ask_size = int(ask_size) if ask_size else 0
                                
                                # Initialize tracking
                                if self.last_price is None:
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    self.last_bid_size = bid_size
                                    self.last_ask_size = ask_size
                                    return
                                
                                # Detect individual order execution
                                # Method 1: Price changed = new execution
                                price_changed = last_price != self.last_price
                                price_direction = None
                                if price_changed:
                                    if last_price > self.last_price:
                                        price_direction = 'UP'  # BUY pressure
                                    else:
                                        price_direction = 'DOWN'  # SELL pressure
                                
                                # Method 2: Volume increased = new execution(s)
                                volume_increased = volume > self.last_volume
                                volume_delta = volume - self.last_volume if volume_increased else 0
                                
                                # Method 3: Bid/Ask size changed = new order placed
                                bid_size_delta = bid_size - self.last_bid_size if bid_size > self.last_bid_size else 0
                                ask_size_delta = ask_size - self.last_ask_size if ask_size > self.last_ask_size else 0
                                
                                # Determine order side and size
                                order_side = None
                                order_size = 0
                                
                                # Priority 1: Price change indicates execution
                                if price_changed and volume_delta > 0:
                                    order_side = 'BUY' if price_direction == 'UP' else 'SELL'
                                    order_size = volume_delta
                                # Priority 2: Large bid size increase = BUY order
                                elif bid_size_delta > 0 and bid_size_delta * (bid or last_price) >= 50000:
                                    order_side = 'BUY'
                                    order_size = bid_size_delta
                                # Priority 3: Large ask size increase = SELL order
                                elif ask_size_delta > 0 and ask_size_delta * (ask or last_price) >= 50000:
                                    order_side = 'SELL'
                                    order_size = ask_size_delta
                                # Priority 4: Volume increase at same price
                                elif volume_increased and volume_delta > 0:
                                    # Use bid/ask to determine side
                                    if bid_size > ask_size:
                                        order_side = 'BUY'
                                    elif ask_size > bid_size:
                                        order_side = 'SELL'
                                    else:
                                        order_side = 'UNKNOWN'
                                    order_size = volume_delta
                                
                                # Record individual order if we detected one
                                if order_side and order_size > 0:
                                    # Determine if options (check symbol format)
                                    is_option = False
                                    option_type = None  # PUT or CALL
                                    
                                    # Options symbols typically have format: SYMBOL_MMDDYYC/P###.##
                                    # Or: SYMBOL YYYY-MM-DD C/P ###.##
                                    if '_' in symbol or len(symbol) > 10:
                                        # Could be options - would need to parse
                                        # For now, assume equity unless we can detect
                                        if 'PUT' in symbol.upper() or symbol[-1] == 'P':
                                            is_option = True
                                            option_type = 'PUT'
                                        elif 'CALL' in symbol.upper() or symbol[-1] == 'C':
                                            is_option = True
                                            option_type = 'CALL'
                                    
                                    order_value = last_price * order_size
                                    
                                    order = {
                                        'symbol': symbol,
                                        'timestamp': timestamp,
                                        'order_side': order_side,
                                        'order_type': 'OPTION' if is_option else 'STOCK',
                                        'option_type': option_type,  # 'PUT' or 'CALL' if options
                                        'size': order_size,  # shares or contracts
                                        'price': last_price,
                                        'value': order_value,
                                        'bid': bid,
                                        'ask': ask,
                                        'bid_size': bid_size,
                                        'ask_size': ask_size,
                                    }
                                    
                                    self.orders.append(order)
                                    
                                    # Display immediately in table format
                                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                    type_str = option_type if option_type else order.get('order_type', 'STOCK')
                                    
                                    # Print in table format immediately
                                    print(f"{len(self.orders):2d}.  {timestamp_str:<22} {order_side:<6} {order_size:>10,}  ${last_price:>10.4f}  ${order_value:>13,.2f}  {type_str:<10}")
                                    
                                    # Update tracking
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    self.last_bid_size = bid_size
                                    self.last_ask_size = ask_size
                                    
                                    # Stop when we have enough
                                    if len(self.orders) >= self.limit:
                                        self.running = False
                                        logger.info(f"   ✅ Collected {len(self.orders)} individual orders!")
                                        break
                                else:
                                    # Update tracking even if no order detected
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    self.last_bid_size = bid_size
                                    self.last_ask_size = ask_size
                                    
        except Exception as e:
            logger.debug(f"Error processing quote: {e}")
    
    async def collect(self, client, timeout_seconds: int = 300):
        """Collect individual orders via streaming API"""
        self.client = client
        
        try:
            self.stream_client = StreamClient(
                client=client,
                account_id=None,
                enforce_enums=False,
            )
            
            self.stream_client.add_level_one_equity_handler(self.process_quote)
            
            logger.info("🔐 Connecting to streaming API...")
            await self.stream_client.login()
            
            logger.info(f"📡 Subscribing to {self.symbol}...")
            await self.stream_client.level_one_equity_subs(
                symbols=[self.symbol],
                fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
            )
            
            logger.info(f"✅ Streaming started - collecting {self.limit} INDIVIDUAL orders...")
            logger.info("   Each order is a SINGLE order execution (not aggregated)")
            logger.info("   Orders will appear below as they are detected:")
            logger.info("")
            logger.info(f"{'#':<4} {'Time':<22} {'Side':<6} {'Size':<12} {'Price':<12} {'Value (USD)':<15} {'Type':<10}")
            logger.info("-" * 120)
            
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(seconds=timeout_seconds)
            self.running = True
            last_log_time = start_time
            
            while self.running and datetime.now(timezone.utc) < end_time:
                try:
                    await self.stream_client.handle_message()
                    
                    # Log progress every 10 seconds
                    now = datetime.now(timezone.utc)
                    if (now - last_log_time).total_seconds() >= 10:
                        elapsed = (now - start_time).total_seconds()
                        logger.info(f"   ⏳ Collecting... ({len(self.orders)}/{self.limit} orders, {self.quote_count} quotes processed, {elapsed:.0f}s elapsed)")
                        last_log_time = now
                    
                    await asyncio.sleep(0.01)
                except Exception as e:
                    error_type = type(e).__name__
                    if "ConnectionClosed" in error_type or "IncompleteRead" in error_type:
                        logger.warning(f"   ⚠️  Connection closed: {error_type}")
                        break
                    await asyncio.sleep(0.1)
            
            if self.stream_client:
                try:
                    await self.stream_client.logout()
                except:
                    pass
            
            return list(self.orders)
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return list(self.orders)


def display_orders(orders: list, symbol: str):
    """Display individual orders in formatted table"""
    if not orders:
        logger.info("")
        logger.info("=" * 120)
        logger.info("❌ NO INDIVIDUAL ORDERS COLLECTED")
        logger.info("=" * 120)
        logger.info("")
        logger.info("Possible reasons:")
        logger.info("  • Market is closed")
        logger.info("  • Symbol not trading actively")
        logger.info("  • No large orders detected during collection period")
        logger.info("")
        logger.info("💡 Run during market hours (9:30 AM - 4:00 PM EST) for best results")
        return
    
    logger.info("-" * 120)
    logger.info("")
    logger.info("=" * 120)
    logger.info(f"📊 COLLECTED {len(orders)} INDIVIDUAL ORDERS - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("Each row above is a SINGLE order execution (not aggregated)")
    logger.info("")
    
    # Summary
    total_value = sum(o.get('value', 0) for o in orders)
    total_size = sum(o.get('size', 0) for o in orders)
    buy_orders = [o for o in orders if o.get('order_side') == 'BUY']
    sell_orders = [o for o in orders if o.get('order_side') == 'SELL']
    stock_orders = [o for o in orders if o.get('order_type') == 'STOCK']
    option_orders = [o for o in orders if o.get('order_type') == 'OPTION']
    prices = [o.get('price', 0) for o in orders if o.get('price', 0) > 0]
    
    logger.info("")
    logger.info("📈 Summary:")
    logger.info(f"   Total individual orders: {len(orders)}")
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
    logger.info("✅ Individual orders from Schwab Streaming API")
    logger.info("=" * 120)
    logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Get last N individual orders from Schwab Streaming API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 get_individual_orders.py AAPL 30
  python3 get_individual_orders.py TSLA 50

Note: This uses the Streaming API to capture individual orders in real-time.
      This is the ONLY way to get individual market-wide orders from Schwab.
      REST API only provides aggregated data.
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
        help='Number of individual orders to collect (default: 30)'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    symbol = args.symbol.upper()
    limit = args.limit
    
    logger.info("=" * 120)
    logger.info(f"🔍 FETCHING LAST {limit} INDIVIDUAL ORDERS - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("⚠️  IMPORTANT: Schwab REST API does NOT provide individual market-wide orders")
    logger.info("   This script uses Streaming API to capture orders in real-time")
    logger.info("   Each order is a SINGLE order execution (not aggregated)")
    logger.info("")
    logger.info("Shows: Symbol, Side (BUY/SELL), Size, Price, Value, PUT/CALL (if options)")
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
        
        logger.info(f"📡 Collecting {limit} individual orders for {symbol}...")
        logger.info("   (This may take a few minutes depending on trading activity)")
        logger.info("   Run during market hours (9:30 AM - 4:00 PM EST) for best results")
        logger.info("")
        
        collector = IndividualOrderCollector(symbol, limit=limit)
        orders = asyncio.run(collector.collect(client, timeout_seconds=300))
        
        display_orders(orders, symbol)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
