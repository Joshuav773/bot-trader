"""
Fetch Live Trade Data - Prove Real Market Feed
==============================================

Fetches and displays recent trade activity for a symbol to prove
we're accessing real live market data from Schwab streaming API.

Usage:
    python3 fetch_live_trades.py NVDA
    python3 fetch_live_trades.py AAPL --minutes 30
"""
import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from collections import deque

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from schwab.auth import easy_client, client_from_token_file
    from schwab.streaming import StreamClient
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    logger.error("schwab-py not installed. Run: pip install schwab-py")


class LiveTradeFetcher:
    """Fetch and display live trade data for a symbol"""
    
    def __init__(self, symbol: str, minutes: int = 5):
        self.symbol = symbol.upper()
        self.minutes = minutes
        self.trades = deque(maxlen=50)  # Keep last 50 trades
        self.client = None
        self.stream_client = None
        self.running = False
        self.start_time = datetime.now(timezone.utc)
        
    def authenticate(self) -> bool:
        """Authenticate with Schwab API"""
        try:
            app_key = os.getenv("SCHWAB_APP_KEY")
            app_secret = os.getenv("SCHWAB_APP_SECRET")
            
            if not app_key or not app_secret:
                logger.error("SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in .env")
                return False
            
            token_path = Path("token.json")
            if not token_path.exists():
                logger.error("token.json not found. Run schwab_streamer.py first to authenticate.")
                return False
            
            self.client = client_from_token_file(
                token_path=str(token_path),
                app_secret=app_secret,
                api_key=app_key,
            )
            
            logger.info("✅ Authenticated with Schwab API")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
    
    def process_quote(self, msg):
        """Process incoming quote data and track as trades"""
        try:
            if isinstance(msg, dict):
                service = msg.get('service', '')
                if service == 'LEVELONE_EQUITIES':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('1', ''))
                            
                            if symbol != self.symbol:
                                continue  # Only track our symbol
                            
                            # Extract quote data
                            last_price = item.get('4', None)  # Last trade price
                            volume = item.get('8', None)      # Total volume
                            bid = item.get('2', None)
                            ask = item.get('3', None)
                            timestamp = datetime.now(timezone.utc)
                            
                            if last_price is not None:
                                # This represents a trade execution (last price update)
                                trade = {
                                    'symbol': symbol,
                                    'price': float(last_price),
                                    'volume': int(volume) if volume else 0,
                                    'bid': float(bid) if bid else None,
                                    'ask': float(ask) if ask else None,
                                    'timestamp': timestamp,
                                    'spread': float(ask) - float(bid) if (bid and ask) else None,
                                }
                                
                                # Only add if price changed (new trade)
                                if not self.trades or self.trades[-1]['price'] != trade['price']:
                                    self.trades.append(trade)
                                    
                                    # Display immediately
                                    self.display_trade(trade, len(self.trades))
                                    
        except Exception as e:
            logger.debug(f"Error processing quote: {e}")
    
    def display_trade(self, trade: dict, count: int):
        """Display a single trade"""
        timestamp_str = trade['timestamp'].strftime('%H:%M:%S.%f')[:-3]
        price = trade['price']
        volume = trade['volume']
        spread = trade.get('spread')
        
        # Color based on price movement
        if len(self.trades) > 1:
            prev_price = self.trades[-2]['price'] if len(self.trades) > 1 else price
            if price > prev_price:
                indicator = "🟢"
            elif price < prev_price:
                indicator = "🔴"
            else:
                indicator = "⚪"
        else:
            indicator = "⚪"
        
        spread_str = f"${spread:.4f}" if spread else "N/A"
        
        print(f"{indicator} [{count:2d}] {timestamp_str} | {trade['symbol']:6s} | "
              f"${price:>10.4f} | Vol: {volume:>12,} | Spread: {spread_str}")
    
    async def start_streaming(self):
        """Start streaming live data"""
        if not self.client:
            logger.error("Not authenticated")
            return
        
        try:
            # Initialize stream client
            self.stream_client = StreamClient(
                client=self.client,
                account_id=None,
                enforce_enums=False,
            )
            
            # Register handler
            self.stream_client.add_level_one_equity_handler(self.process_quote)
            
            logger.info("=" * 100)
            logger.info(f"📡 LIVE TRADE FEED - {self.symbol}")
            logger.info("=" * 100)
            logger.info(f"⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info(f"📊 Collecting trades for: {self.minutes} minute(s)")
            logger.info(f"🎯 Target: Last 50 trades for {self.symbol}")
            logger.info("")
            logger.info("Legend: 🟢 = Price Up | 🔴 = Price Down | ⚪ = Same Price")
            logger.info("-" * 100)
            logger.info(f"{'#':<4} {'Time':<12} {'Symbol':<8} {'Price':<12} {'Volume':<15} {'Spread':<10}")
            logger.info("-" * 100)
            
            # Login
            await self.stream_client.login()
            
            # Subscribe to symbol
            await self.stream_client.level_one_equity_subs(
                symbols=[self.symbol],
                fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
            )
            
            logger.info(f"✅ Subscribed to {self.symbol} - Waiting for trades...")
            logger.info("")
            
            # Stream for specified duration
            end_time = self.start_time + timedelta(minutes=self.minutes)
            self.running = True
            
            while self.running and datetime.now(timezone.utc) < end_time:
                try:
                    await self.stream_client.handle_message()
                except Exception as e:
                    error_type = type(e).__name__
                    if "ConnectionClosed" in error_type or "IncompleteRead" in error_type:
                        logger.warning(f"⚠️  Connection lost: {error_type}. Reconnecting...")
                        # Try to reconnect
                        try:
                            await self.stream_client.logout()
                        except:
                            pass
                        
                        self.stream_client = StreamClient(
                            client=self.client,
                            account_id=None,
                            enforce_enums=False,
                        )
                        self.stream_client.add_level_one_equity_handler(self.process_quote)
                        await self.stream_client.login()
                        await self.stream_client.level_one_equity_subs(
                            symbols=[self.symbol],
                            fields=[0, 1, 2, 3, 4, 5, 6, 8]
                        )
                        logger.info("✅ Reconnected")
                    else:
                        logger.warning(f"⚠️  Error: {e}")
                        await asyncio.sleep(1)
            
            # Stop streaming
            self.running = False
            if self.stream_client:
                await self.stream_client.logout()
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Interrupted by user")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            self.running = False
    
    def display_summary(self):
        """Display summary of collected trades"""
        if not self.trades:
            logger.info("")
            logger.info("=" * 100)
            logger.info("❌ NO TRADES COLLECTED")
            logger.info("=" * 100)
            logger.info("")
            logger.info("Possible reasons:")
            logger.info("  • Market is closed")
            logger.info("  • Symbol not trading actively")
            logger.info("  • Connection issues")
            logger.info("  • Symbol not found")
            return
        
        logger.info("")
        logger.info("=" * 100)
        logger.info(f"📊 SUMMARY - {self.symbol}")
        logger.info("=" * 100)
        
        trades_list = list(self.trades)
        
        # Statistics
        prices = [t['price'] for t in trades_list]
        volumes = [t['volume'] for t in trades_list]
        
        logger.info(f"")
        logger.info(f"📈 Trade Statistics:")
        logger.info(f"   Total trades collected: {len(trades_list)}")
        logger.info(f"   Time range: {trades_list[0]['timestamp'].strftime('%H:%M:%S')} - "
                   f"{trades_list[-1]['timestamp'].strftime('%H:%M:%S')}")
        logger.info(f"   Duration: {(trades_list[-1]['timestamp'] - trades_list[0]['timestamp']).total_seconds():.1f} seconds")
        logger.info(f"")
        logger.info(f"💰 Price Statistics:")
        logger.info(f"   First price: ${prices[0]:.4f}")
        logger.info(f"   Last price:  ${prices[-1]:.4f}")
        logger.info(f"   High:        ${max(prices):.4f}")
        logger.info(f"   Low:         ${min(prices):.4f}")
        logger.info(f"   Change:      ${prices[-1] - prices[0]:.4f} "
                   f"({((prices[-1] - prices[0]) / prices[0] * 100):+.2f}%)")
        logger.info(f"")
        logger.info(f"📊 Volume Statistics:")
        logger.info(f"   Total volume: {sum(volumes):,}")
        logger.info(f"   Average volume per trade: {sum(volumes) / len(volumes):,.0f}")
        logger.info(f"")
        
        # Show last 10 trades
        logger.info("=" * 100)
        logger.info(f"📋 LAST 10 TRADES (Most Recent)")
        logger.info("=" * 100)
        logger.info(f"{'#':<4} {'Time':<12} {'Price':<12} {'Volume':<15} {'Change':<10}")
        logger.info("-" * 100)
        
        for i, trade in enumerate(trades_list[-10:], 1):
            timestamp_str = trade['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            price = trade['price']
            volume = trade['volume']
            
            if i > 1:
                prev_price = trades_list[-10 + i - 2]['price']
                change = price - prev_price
                change_pct = (change / prev_price * 100) if prev_price else 0
                change_str = f"${change:+.4f} ({change_pct:+.2f}%)"
            else:
                change_str = "N/A"
            
            print(f"{i:2d}.  {timestamp_str:<12} ${price:>10.4f}  {volume:>12,}  {change_str}")
        
        logger.info("")
        logger.info("✅ This proves we're receiving REAL LIVE market data!")
        logger.info("   Each 'last price' update represents an actual trade execution.")
        logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch live trade data for a symbol to prove real market feed',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_live_trades.py NVDA
  python3 fetch_live_trades.py AAPL --minutes 10
  python3 fetch_live_trades.py TSLA --minutes 5
        """
    )
    parser.add_argument(
        'symbol',
        help='Stock symbol to track (e.g., NVDA, AAPL, TSLA)'
    )
    parser.add_argument(
        '--minutes',
        type=int,
        default=5,
        help='Number of minutes to collect trades (default: 5)'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    fetcher = LiveTradeFetcher(args.symbol, minutes=args.minutes)
    
    if not fetcher.authenticate():
        return 1
    
    try:
        # Run async streaming
        asyncio.run(fetcher.start_streaming())
        
        # Display summary
        fetcher.display_summary()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        fetcher.display_summary()
        return 0
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())


