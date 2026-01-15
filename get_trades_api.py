"""
Get Last 50 Trades from Schwab API
===================================

Makes direct API calls to fetch the last 50 trades/price updates for a symbol.

Usage:
    python3 get_trades_api.py NVDA
    python3 get_trades_api.py AAPL
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


def get_price_history(client, symbol: str, minutes: int = 60):
    """Get price history for a symbol"""
    try:
        # Try different methods to get price history
        methods_to_try = [
            'get_price_history_every_minute',
            'get_price_history',
            'get_price_history_every_day',
            'get_price_history_every_week',
        ]
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=minutes)
        
        for method_name in methods_to_try:
            if hasattr(client, method_name):
                method = getattr(client, method_name)
                logger.info(f"Trying {method_name}...")
                
                try:
                    # Try with datetime objects
                    result = method(
                        symbol,
                        start_datetime=start_time,
                        end_datetime=end_time
                    )
                    
                    # Handle Response object
                    if hasattr(result, 'status_code'):
                        if result.status_code == 200:
                            data = result.json()
                            return data
                        else:
                            logger.warning(f"{method_name} returned status {result.status_code}")
                            continue
                    elif isinstance(result, dict):
                        return result
                    else:
                        logger.warning(f"{method_name} returned unexpected type: {type(result)}")
                        continue
                        
                except TypeError as e:
                    # Try with different parameter names
                    try:
                        result = method(symbol, start_datetime=start_time, end_datetime=end_time)
                        if hasattr(result, 'json'):
                            return result.json()
                        return result
                    except:
                        try:
                            # Try with epoch timestamps
                            start_epoch = int(start_time.timestamp() * 1000)
                            end_epoch = int(end_time.timestamp() * 1000)
                            result = method(symbol, start_date=start_epoch, end_date=end_epoch)
                            if hasattr(result, 'json'):
                                return result.json()
                            return result
                        except Exception as e2:
                            logger.debug(f"{method_name} failed with different params: {e2}")
                            continue
                except Exception as e:
                    logger.debug(f"{method_name} failed: {e}")
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting price history: {e}")
        return None


def get_quote(client, symbol: str):
    """Get current quote for a symbol"""
    try:
        methods_to_try = [
            'get_quote',
            'get_quotes',
            'quote',
        ]
        
        for method_name in methods_to_try:
            if hasattr(client, method_name):
                method = getattr(client, method_name)
                try:
                    result = method(symbol)
                    
                    if hasattr(result, 'status_code'):
                        if result.status_code == 200:
                            return result.json()
                        continue
                    elif isinstance(result, dict):
                        return result
                    elif isinstance(result, list):
                        return result[0] if result else None
                except Exception as e:
                    logger.debug(f"{method_name} failed: {e}")
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting quote: {e}")
        return None


def format_price_data(data, symbol: str):
    """Format price history data as trades"""
    trades = []
    
    if not data:
        return trades
    
    # Handle different response formats
    candles = None
    if isinstance(data, dict):
        if 'candles' in data:
            candles = data['candles']
        elif 'data' in data:
            candles = data['data']
        elif 'priceHistory' in data:
            candles = data['priceHistory']
    elif isinstance(data, list):
        candles = data
    
    if not candles:
        logger.warning("No candles/data found in response")
        return trades
    
    # Convert candles to trade-like format
    for candle in candles[-50:]:  # Last 50
        if isinstance(candle, dict):
            trade = {
                'symbol': symbol,
                'timestamp': candle.get('datetime', candle.get('time', candle.get('timestamp'))),
                'price': candle.get('close', candle.get('price', candle.get('last'))),
                'open': candle.get('open'),
                'high': candle.get('high'),
                'low': candle.get('low'),
                'volume': candle.get('volume', 0),
            }
            trades.append(trade)
    
    return trades


def display_trades(trades: list, symbol: str):
    """Display trades in formatted table"""
    if not trades:
        logger.info(f"\n❌ No trades found for {symbol}")
        return
    
    logger.info("")
    logger.info("=" * 100)
    logger.info(f"📊 LAST {len(trades)} TRADES/PRICE UPDATES - {symbol}")
    logger.info("=" * 100)
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<20} {'Price':<12} {'Open':<12} {'High':<12} {'Low':<12} {'Volume':<15}")
    logger.info("-" * 100)
    
    for i, trade in enumerate(trades, 1):
        timestamp = trade.get('timestamp', 'N/A')
        
        # Format timestamp
        if isinstance(timestamp, (int, float)):
            if timestamp > 1e10:
                timestamp = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:
                timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                timestamp_str = str(timestamp)[:19]
        else:
            timestamp_str = str(timestamp)[:19]
        
        price = trade.get('price', 0)
        open_price = trade.get('open', price)
        high = trade.get('high', price)
        low = trade.get('low', price)
        volume = trade.get('volume', 0)
        
        print(f"{i:2d}.  {timestamp_str:<20} ${price:>10.4f}  ${open_price:>10.4f}  "
              f"${high:>10.4f}  ${low:>10.4f}  {volume:>12,}")
    
    logger.info("-" * 100)
    
    # Statistics
    if trades:
        prices = [t.get('price', 0) for t in trades if t.get('price')]
        volumes = [t.get('volume', 0) for t in trades if t.get('volume')]
        
        if prices:
            logger.info("")
            logger.info(f"📈 Statistics:")
            logger.info(f"   First price: ${prices[0]:.4f}")
            logger.info(f"   Last price:  ${prices[-1]:.4f}")
            logger.info(f"   High:        ${max(prices):.4f}")
            logger.info(f"   Low:         ${min(prices):.4f}")
            logger.info(f"   Change:      ${prices[-1] - prices[0]:.4f} "
                       f"({((prices[-1] - prices[0]) / prices[0] * 100):+.2f}%)")
        
        if volumes:
            logger.info(f"   Total volume: {sum(volumes):,}")
    
    logger.info("")
    logger.info("✅ This data comes directly from Schwab API!")
    logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Get last 50 trades from Schwab API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 get_trades_api.py NVDA
  python3 get_trades_api.py AAPL
  python3 get_trades_api.py TSLA
        """
    )
    parser.add_argument(
        'symbol',
        help='Stock symbol (e.g., NVDA, AAPL, TSLA)'
    )
    parser.add_argument(
        '--minutes',
        type=int,
        default=60,
        help='Number of minutes to look back (default: 60)'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    symbol = args.symbol.upper()
    
    # Authenticate
    logger.info("=" * 100)
    logger.info("🔍 FETCHING TRADES FROM SCHWAB API")
    logger.info("=" * 100)
    logger.info(f"📋 Symbol: {symbol}")
    logger.info(f"⏰ Time range: Last {args.minutes} minutes")
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
        
        # Try to get price history
        logger.info("📡 Fetching price history from API...")
        price_data = get_price_history(client, symbol, minutes=args.minutes)
        
        if price_data:
            logger.info("✅ Received price history data")
            trades = format_price_data(price_data, symbol)
            display_trades(trades, symbol)
        else:
            logger.warning("⚠️  Could not get price history. Trying quote endpoint...")
            
            # Fallback: Get current quote
            quote = get_quote(client, symbol)
            if quote:
                logger.info("✅ Received quote data")
                # Format as single trade
                trade = {
                    'symbol': symbol,
                    'timestamp': datetime.now(timezone.utc),
                    'price': quote.get('lastPrice', quote.get('last', quote.get('close'))),
                    'volume': quote.get('totalVolume', quote.get('volume', 0)),
                }
                display_trades([trade], symbol)
            else:
                logger.error("❌ Could not fetch any data from API")
                logger.info("")
                logger.info("💡 Available methods on client:")
                methods = [m for m in dir(client) if not m.startswith('_') and callable(getattr(client, m))]
                price_methods = [m for m in methods if 'price' in m.lower() or 'quote' in m.lower() or 'market' in m.lower()]
                for m in sorted(price_methods)[:20]:
                    logger.info(f"   - {m}")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())


