"""
Test: Visualize Last 30 Individual Trades
==========================================

Quick test to fetch and visualize the last 30 individual trades from Schwab API.
This helps determine how alerts should be formatted.

Usage:
    python3 test_orders_visualization.py TSLA
    python3 test_orders_visualization.py NVDA
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


class TradeCollector:
    """Collect individual trades for visualization"""
    
    def __init__(self, symbol: str, limit: int = 30):
        self.symbol = symbol.upper()
        self.limit = limit
        self.trades = deque(maxlen=limit)
        self.stream_client = None
        self.client = None
        self.running = False
        self.last_volume = None
        self.last_price = None
        
    def process_quote(self, msg):
        """Process incoming quote and extract individual trades"""
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
                            timestamp = datetime.now(timezone.utc)
                            
                            if last_price is not None:
                                last_price = float(last_price)
                                volume = int(volume) if volume else 0
                                
                                # Initialize tracking
                                if self.last_price is None:
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    return
                                
                                # Detect individual trade: price change OR volume increase = new execution
                                price_changed = last_price != self.last_price
                                volume_increased = volume > self.last_volume
                                
                                if price_changed or volume_increased:
                                    # Calculate trade volume from volume delta
                                    if volume > self.last_volume:
                                        trade_volume = volume - self.last_volume
                                    else:
                                        trade_volume = 1  # Minimum - price changed but volume didn't update yet
                                    
                                    # Only record if we have meaningful volume
                                    if trade_volume > 0:
                                        trade = {
                                            'symbol': symbol,
                                            'timestamp': timestamp,
                                            'price': last_price,
                                            'volume': trade_volume,
                                            'bid': float(bid) if bid else None,
                                            'ask': float(ask) if ask else None,
                                            'trade_value': last_price * trade_volume,
                                        }
                                        
                                        self.trades.append(trade)
                                        
                                        # Log progress
                                        if len(self.trades) % 5 == 0:
                                            logger.info(f"   Collected {len(self.trades)}/{self.limit} trades...")
                                    
                                    # Update tracking
                                    self.last_price = last_price
                                    self.last_volume = volume
                                    
                                    # Stop when we have enough
                                    if len(self.trades) >= self.limit:
                                        self.running = False
                                        logger.info(f"   ✅ Collected {len(self.trades)} trades!")
                                        break
                                    
        except Exception as e:
            logger.debug(f"Error processing quote: {e}")
    
    async def collect(self, client, timeout_seconds: int = 180):
        """Collect trades via streaming API"""
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
                fields=[0, 1, 2, 3, 4, 8]  # Symbol, Bid, Ask, Last, Volume
            )
            
            logger.info(f"✅ Streaming - collecting {self.limit} individual trades...")
            logger.info("   Waiting for trade activity...")
            logger.info("")
            
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
                        logger.info(f"   ⏳ Still collecting... ({len(self.trades)}/{self.limit} trades, {elapsed:.0f}s elapsed)")
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
            
            return list(self.trades)
            
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return list(self.trades)


def display_trades(trades: list, symbol: str):
    """Display trades in clear format for visualization"""
    if not trades:
        logger.info("")
        logger.info("=" * 100)
        logger.info("❌ NO TRADES COLLECTED")
        logger.info("=" * 100)
        logger.info("")
        logger.info("Market may be closed or symbol not trading actively.")
        return
    
    logger.info("")
    logger.info("=" * 100)
    logger.info(f"📊 LAST {len(trades)} INDIVIDUAL TRADES - {symbol}")
    logger.info("=" * 100)
    logger.info("")
    logger.info("This is how individual trade alerts will look:")
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<20} {'Price':<12} {'Volume':<12} {'Value':<15} {'Side':<6}")
    logger.info("-" * 100)
    
    prev_price = None
    for i, trade in enumerate(trades, 1):
        timestamp = trade.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        else:
            timestamp_str = str(timestamp)[:23]
        
        price = trade.get('price', 0)
        volume = trade.get('volume', 0)
        trade_value = trade.get('trade_value', 0)
        
        # Determine side (buy/sell) based on price movement
        if prev_price is not None:
            if price > prev_price:
                side = "BUY"
            elif price < prev_price:
                side = "SELL"
            else:
                side = "---"
        else:
            side = "---"
        
        prev_price = price
        
        print(f"{i:2d}.  {timestamp_str:<20} ${price:>10.4f}  {volume:>10,}  ${trade_value:>13,.2f}  {side:<6}")
    
    logger.info("-" * 100)
    
    # Summary
    total_value = sum(t.get('trade_value', 0) for t in trades)
    total_volume = sum(t.get('volume', 0) for t in trades)
    prices = [t.get('price', 0) for t in trades]
    
    logger.info("")
    logger.info("📈 Summary:")
    logger.info(f"   Total trades: {len(trades)}")
    logger.info(f"   Total volume: {total_volume:,} shares")
    logger.info(f"   Total value: ${total_value:,.2f}")
    if prices:
        logger.info(f"   Price range: ${min(prices):.4f} - ${max(prices):.4f}")
    logger.info("")
    logger.info("=" * 100)
    logger.info("💡 Use this format to design your alert notifications")
    logger.info("=" * 100)
    logger.info("")


def check_market_hours():
    """Check if market is currently open"""
    try:
        from datetime import datetime
        import pytz
        
        now_est = datetime.now(pytz.timezone('US/Eastern'))
        hour = now_est.hour
        minute = now_est.minute
        
        # Market hours: 9:30 AM - 4:00 PM EST
        is_open = (hour > 9 or (hour == 9 and minute >= 30)) and hour < 16
        
        return is_open, now_est
    except:
        return None, None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test: Visualize last 30 individual trades for alert formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_orders_visualization.py TSLA
  python3 test_orders_visualization.py NVDA
        """
    )
    parser.add_argument(
        'symbol',
        help='Stock symbol (e.g., NVDA, AAPL, TSLA)'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    symbol = args.symbol.upper()
    
    # Check market hours
    market_open, est_time = check_market_hours()
    
    logger.info("=" * 100)
    logger.info(f"🧪 TEST: VISUALIZE INDIVIDUAL TRADES - {symbol}")
    logger.info("=" * 100)
    logger.info("")
    logger.info("Purpose: Fetch last 30 individual trades to visualize alert format")
    logger.info("")
    
    if market_open is not None:
        if est_time:
            logger.info(f"⏰ Current time (EST): {est_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        if not market_open:
            logger.warning("⚠️  Market is CLOSED (9:30 AM - 4:00 PM EST)")
            logger.warning("   Script will still connect but may not collect trades")
            logger.warning("   For best results, run during market hours")
            logger.info("")
        else:
            logger.info("✅ Market is OPEN")
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
        
        # Collect 30 individual trades
        logger.info(f"📡 Fetching last 30 individual trades for {symbol}...")
        logger.info("   (This may take 1-2 minutes depending on trading activity)")
        logger.info("")
        
        collector = TradeCollector(symbol, limit=30)
        trades = asyncio.run(collector.collect(client, timeout_seconds=120))
        
        # Display for visualization
        display_trades(trades, symbol)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

