"""
Get Last N Trades from Schwab API
==================================

Fetches the last N trades from Schwab Price History API for a specific ticker.
Each data point represents trade activity for that time period.

Usage:
    python3 get_last_trades.py AAPL 30
    python3 get_last_trades.py TSLA 50
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


def get_price_history(client, symbol: str, limit: int = 30):
    """Get price history (trades) from Schwab API"""
    try:
        # Calculate time window (need enough minutes to get N trades)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)  # Last 24 hours
        
        # Try different methods
        methods_to_try = [
            'get_price_history_every_minute',
            'get_price_history',
        ]
        
        for method_name in methods_to_try:
            if hasattr(client, method_name):
                try:
                    method = getattr(client, method_name)
                    logger.info(f"   Using {method_name}...")
                    
                    result = method(symbol, start_datetime=start_time, end_datetime=end_time)
                    
                    # Handle response
                    if hasattr(result, 'json'):
                        data = result.json()
                    elif hasattr(result, 'status_code'):
                        if result.status_code == 200:
                            data = result.json()
                        else:
                            continue
                    elif isinstance(result, dict):
                        data = result
                    else:
                        continue
                    
                    # Extract candles
                    candles = data.get('candles', data.get('data', data.get('priceHistory', [])))
                    
                    if candles and isinstance(candles, list):
                        logger.info(f"   ✅ Found {len(candles)} data points")
                        return candles[-limit:]  # Last N
                    
                except Exception as e:
                    logger.debug(f"   {method_name} failed: {e}")
                    continue
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting price history: {e}", exc_info=True)
        return []


def format_as_trades(candles: list, symbol: str):
    """Format price history candles as individual trades"""
    trades = []
    
    for candle in candles:
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
        
        trade = {
            'symbol': symbol.upper(),
            'timestamp': timestamp,
            'price': float(close_price) if close_price else 0.0,
            'volume': int(volume) if volume else 0,
            'open': float(open_price) if open_price else 0.0,
            'high': float(high) if high else 0.0,
            'low': float(low) if low else 0.0,
            'trade_value': float(close_price) * int(volume) if (close_price and volume) else 0.0,
        }
        
        trades.append(trade)
    
    return trades


def display_trades(trades: list, symbol: str):
    """Display trades in formatted table"""
    if not trades:
        logger.info("")
        logger.info("=" * 100)
        logger.info("❌ NO TRADES FOUND")
        logger.info("=" * 100)
        return
    
    logger.info("")
    logger.info("=" * 100)
    logger.info(f"📊 LAST {len(trades)} TRADES - {symbol}")
    logger.info("=" * 100)
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<25} {'Price':<12} {'Volume':<15} {'Value (USD)':<15}")
    logger.info("-" * 100)
    
    for i, trade in enumerate(trades, 1):
        timestamp = trade.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)[:19]
        
        price = trade.get('price', 0)
        volume = trade.get('volume', 0)
        trade_value = trade.get('trade_value', 0)
        
        print(f"{i:2d}.  {timestamp_str:<25} ${price:>10.4f}  {volume:>12,}  ${trade_value:>13,.2f}")
    
    logger.info("-" * 100)
    
    # Summary
    total_value = sum(t.get('trade_value', 0) for t in trades)
    total_volume = sum(t.get('volume', 0) for t in trades)
    prices = [t.get('price', 0) for t in trades if t.get('price', 0) > 0]
    
    logger.info("")
    logger.info("📈 Summary:")
    logger.info(f"   Total trades: {len(trades)}")
    logger.info(f"   Total volume: {total_volume:,} shares")
    logger.info(f"   Total value: ${total_value:,.2f}")
    if prices:
        logger.info(f"   Price range: ${min(prices):.4f} - ${max(prices):.4f}")
    logger.info("")
    logger.info("=" * 100)
    logger.info("✅ Data from Schwab Price History API")
    logger.info("=" * 100)
    logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Get last N trades from Schwab API for a ticker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 get_last_trades.py AAPL 30
  python3 get_last_trades.py TSLA 50
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
        help='Number of trades to fetch (default: 30)'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    symbol = args.symbol.upper()
    limit = args.limit
    
    logger.info("=" * 100)
    logger.info(f"🔍 FETCHING LAST {limit} TRADES - {symbol}")
    logger.info("=" * 100)
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
        
        logger.info(f"📡 Fetching last {limit} trades for {symbol}...")
        candles = get_price_history(client, symbol, limit=limit)
        
        if candles:
            trades = format_as_trades(candles, symbol)
            display_trades(trades, symbol)
        else:
            logger.error("❌ Could not fetch trades from API")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
