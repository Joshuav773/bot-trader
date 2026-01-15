#!/usr/bin/env python3
"""
Test Real Stream with Historical Data
=====================================

Fetches historical data from Schwab API for NVDA (yesterday),
then simulates it as a live stream to test the streamer's detection logic.

This shows:
- Real console output as orders are detected
- Actual notifications being sent
- How the streamer would process real market data

Usage:
    python3 test_real_stream.py NVDA 30
    python3 test_real_stream.py NVDA 50 --yesterday
"""
import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging to match streamer format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import streamer components
try:
    from schwab.client import Client
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    logger.error("schwab-py not installed")

try:
    from order_tracker import LargeOrderTracker
    from trade_tracker import LargeTradeTracker
    from notifications import get_notification_service
    from db import get_db
    STREAMER_COMPONENTS_AVAILABLE = True
except ImportError as e:
    STREAMER_COMPONENTS_AVAILABLE = False
    logger.error(f"Streamer components not available: {e}")


def fetch_historical_price_data(client, symbol: str, days_back: int = 1, periods: int = 30):
    """
    Fetch historical price data from Schwab API
    
    Returns minute-by-minute OHLCV data that we can simulate as a stream
    """
    try:
        from datetime import datetime, timedelta
        
        # Calculate start and end times (yesterday)
        end_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        start_time = end_time - timedelta(days=1)
        
        # Get price history (minute bars)
        logger.info(f"📡 Fetching historical data for {symbol} from {start_time.date()}...")
        
        # Use get_price_history endpoint
        response = client.get_price_history(
            symbol=symbol,
            period_type=Client.PriceHistory.PeriodType.DAY,
            period=Client.PriceHistory.Period.ONE_DAY,
            frequency_type=Client.PriceHistory.FrequencyType.MINUTE,
            frequency=Client.PriceHistory.Frequency.EVERY_MINUTE,
            start_datetime=start_time,
            end_datetime=end_time,
            need_extended_hours_data=False
        )
        
        if not response or 'candles' not in response:
            logger.warning(f"No price history data returned for {symbol}")
            return []
        
        candles = response.get('candles', [])
        logger.info(f"✅ Fetched {len(candles)} minute bars for {symbol}")
        
        # Convert candles to quote format
        quotes = []
        for candle in candles[:periods]:  # Limit to requested number
            # Create realistic quote data from OHLCV
            open_price = candle.get('open', 0)
            high = candle.get('high', 0)
            low = candle.get('low', 0)
            close = candle.get('close', 0)
            volume = candle.get('volume', 0)
            datetime_ms = candle.get('datetime', 0)
            
            # Convert timestamp
            if datetime_ms:
                timestamp = datetime.fromtimestamp(datetime_ms / 1000, tz=timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            # Create bid/ask spread (typical 0.01-0.10% spread)
            mid_price = close or open_price
            spread_pct = 0.0005  # 0.05% spread
            bid = mid_price * (1 - spread_pct / 2)
            ask = mid_price * (1 + spread_pct / 2)
            
            # Estimate bid/ask sizes (based on volume)
            # Typical: bid/ask sizes are 10-50% of volume for that minute
            size_factor = 0.2  # 20% of volume
            bid_size = int(volume * size_factor) if volume > 0 else 1000
            ask_size = int(volume * size_factor) if volume > 0 else 1000
            
            quote = {
                'symbol': symbol,
                'bid': round(bid, 2),
                'ask': round(ask, 2),
                'bid_size': bid_size,
                'ask_size': ask_size,
                'last': close or open_price,
                'volume': volume,
                'timestamp': timestamp.isoformat(),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
            }
            quotes.append(quote)
        
        return quotes
        
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}", exc_info=True)
        return []


def simulate_order_book_from_quote(quote, order_count: int = 5):
    """
    Simulate order book data from a quote
    Creates realistic bid/ask levels around the current price
    """
    mid_price = quote.get('last', (quote.get('bid', 0) + quote.get('ask', 0)) / 2)
    bid = quote.get('bid', mid_price)
    ask = quote.get('ask', mid_price)
    
    # Create order book levels
    bids = []
    asks = []
    
    # Generate bid levels (below current bid)
    for i in range(order_count):
        price = bid - (i * 0.01)  # $0.01 increments
        size = quote.get('bid_size', 1000) * (1 - i * 0.1)  # Decreasing size
        if price > 0 and size > 0:
            bids.append({'price': round(price, 2), 'size': int(size)})
    
    # Generate ask levels (above current ask)
    for i in range(order_count):
        price = ask + (i * 0.01)  # $0.01 increments
        size = quote.get('ask_size', 1000) * (1 - i * 0.1)  # Decreasing size
        if price > 0 and size > 0:
            asks.append({'price': round(price, 2), 'size': int(size)})
    
    return bids, asks


def process_quote_through_streamer(quote, order_tracker, trade_tracker, db, notification_service):
    """
    Process a quote through the streamer's detection logic
    This simulates what happens in schwab_streamer.py
    """
    symbol = quote.get('symbol')
    detected_items = []
    
    # Process through order tracker
    if order_tracker:
        large_order = order_tracker.process_quote(quote)
        if large_order:
            # Save to database
            if db and db.save_large_order(large_order):
                detection_method = large_order.get('detection_method', 'UNKNOWN')
                logger.info(
                    f"📋 Large {large_order.get('order_type')} order detected ({detection_method}): {symbol} | "
                    f"Value: ${large_order.get('order_value_usd', 0):,.2f} | "
                    f"Size: {large_order.get('order_size_shares', 0):,} shares @ ${large_order.get('price')} | "
                    f"Instrument: {large_order.get('instrument', 'equity')}"
                )
                
                # Send notification
                if notification_service:
                    sent = notification_service.send_order_notification(large_order)
                    if sent > 0:
                        logger.info(f"📧 Sent large order notification to {sent} recipient(s)")
                
                detected_items.append(('order', large_order))
    
    # Process through trade tracker
    if trade_tracker:
        large_trade = trade_tracker.process_quote(quote)
        if large_trade:
            # Save to database
            if db and db.save_large_trade(large_trade):
                detection_method = large_trade.get('detection_method', 'UNKNOWN')
                logger.info(
                    f"💰 Large trade detected ({detection_method}): {symbol} | "
                    f"Value: ${large_trade.get('trade_value_usd', 0):,.2f} | "
                    f"Entry: ${large_trade.get('entry_price')} → Exit: ${large_trade.get('exit_price')} | "
                    f"Vol: {large_trade.get('volume', 0):,}"
                )
                
                # Send notification
                if notification_service:
                    sent = notification_service.send_large_trade_notification(large_trade)
                    if sent > 0:
                        logger.info(f"📧 Sent large trade notification to {sent} recipient(s)")
                
                detected_items.append(('trade', large_trade))
    
    return detected_items


def process_order_book_through_streamer(symbol, bids, asks, book_time, exchange, db, notification_service, scan_all_orders=False):
    """
    Process order book through streamer's scanning logic
    """
    detected_orders = []
    
    # Scan bids
    for bid_order in bids:
        if isinstance(bid_order, dict):
            price = bid_order.get('price')
            size = bid_order.get('size', 0)
            
            if price and size:
                order_value = float(price) * int(size)
                
                # Only process large orders (or all if scan_all_orders)
                if scan_all_orders or order_value >= 50000.0:
                    order_data = {
                        'symbol': symbol,
                        'order_type': 'BUY_ORDER',
                        'order_side': 'BUY',
                        'order_value_usd': order_value,
                        'price': float(price),
                        'order_size_shares': int(size),
                        'order_size_usd': order_value,  # Also include this for email formatting
                        'timestamp': datetime.now(timezone.utc),
                        'instrument': 'equity' if exchange != 'OPTIONS' else 'option',
                        'detection_method': 'ORDER_BOOK_BID',
                        'exchange': exchange,
                        'book_time': book_time,
                        'spread': None,  # For email formatting
                    }
                    
                    if db:
                        if scan_all_orders:
                            db.save_all_order(order_data)
                        else:
                            db.save_large_order(order_data)
                    
                    logger.info(
                        f"📋 Large BUY order in book: {symbol} | "
                        f"Value: ${order_value:,.2f} | "
                        f"Size: {int(size):,} @ ${float(price):.2f} | "
                        f"Exchange: {exchange}"
                    )
                    
                    if notification_service and not scan_all_orders:
                        sent = notification_service.send_order_notification(order_data)
                        if sent > 0:
                            logger.info(f"📧 Sent order notification to {sent} recipient(s)")
                    
                    detected_orders.append(order_data)
    
    # Scan asks
    for ask_order in asks:
        if isinstance(ask_order, dict):
            price = ask_order.get('price')
            size = ask_order.get('size', 0)
            
            if price and size:
                order_value = float(price) * int(size)
                
                # Only process large orders (or all if scan_all_orders)
                if scan_all_orders or order_value >= 50000.0:
                    order_data = {
                        'symbol': symbol,
                        'order_type': 'SELL_ORDER',
                        'order_side': 'SELL',
                        'order_value_usd': order_value,
                        'price': float(price),
                        'order_size_shares': int(size),
                        'order_size_usd': order_value,  # Also include this for email formatting
                        'timestamp': datetime.now(timezone.utc),
                        'instrument': 'equity' if exchange != 'OPTIONS' else 'option',
                        'detection_method': 'ORDER_BOOK_ASK',
                        'exchange': exchange,
                        'book_time': book_time,
                        'spread': None,  # For email formatting
                    }
                    
                    if db:
                        if scan_all_orders:
                            db.save_all_order(order_data)
                        else:
                            db.save_large_order(order_data)
                    
                    logger.info(
                        f"📋 Large SELL order in book: {symbol} | "
                        f"Value: ${order_value:,.2f} | "
                        f"Size: {int(size):,} @ ${float(price):.2f} | "
                        f"Exchange: {exchange}"
                    )
                    
                    if notification_service and not scan_all_orders:
                        sent = notification_service.send_order_notification(order_data)
                        if sent > 0:
                            logger.info(f"📧 Sent order notification to {sent} recipient(s)")
                    
                    detected_orders.append(order_data)
    
    return detected_orders


async def simulate_live_stream(symbol: str, limit: int = 30, days_back: int = 1):
    """
    Fetch historical data and simulate it as a live stream
    """
    if not SCHWAB_AVAILABLE:
        logger.error("Schwab API not available")
        return
    
    if not STREAMER_COMPONENTS_AVAILABLE:
        logger.error("Streamer components not available")
        return
    
    # Authenticate (same method as streamer)
    from schwab.auth import easy_client, client_from_token_file
    
    token_path = Path("token.json")
    app_key = os.getenv("SCHWAB_APP_KEY")
    app_secret = os.getenv("SCHWAB_APP_SECRET")
    
    if not app_key or not app_secret:
        logger.error("SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set")
        return
    
    # Check for token in environment variable (production) or file (local)
    token_json_env = os.getenv("SCHWAB_TOKEN_JSON")
    if token_json_env:
        import json
        try:
            token_data = json.loads(token_json_env)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, 'w') as f:
                json.dump(token_data, f)
            logger.info("Loaded token from SCHWAB_TOKEN_JSON")
        except Exception as e:
            logger.error(f"Failed to parse SCHWAB_TOKEN_JSON: {e}")
            return
    
    try:
        if token_path.exists():
            client = client_from_token_file(
                token_path=str(token_path),
                app_secret=app_secret,
                api_key=app_key,
            )
            logger.info("✅ Authenticated with existing token")
        else:
            logger.error("No token found. Please run schwab_streamer.py first to authenticate.")
            return
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        logger.error("You may need to re-authenticate. Run schwab_streamer.py first.")
        return
    
    # Fetch historical data
    quotes = fetch_historical_price_data(client, symbol, days_back=days_back, periods=limit)
    
    if not quotes:
        logger.warning(f"⚠️  Could not fetch historical data from API (token may be expired)")
        logger.info("📊 Using realistic sample data based on NVDA to demonstrate functionality...")
        logger.info("   (To use real API data, refresh your token by running schwab_streamer.py)")
        logger.info("")
        
        # Create realistic sample data based on NVDA
        base_price = 500.0  # NVDA typical price
        base_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        quotes = []
        for i in range(limit):
            # Simulate price movement
            price_change = (i % 10 - 5) * 0.5  # Oscillating price
            current_price = base_price + price_change
            
            # Simulate volume (higher during price moves)
            base_volume = 5000000
            volume = base_volume + int(abs(price_change) * 100000)
            
            # Create bid/ask spread
            spread = 0.10
            bid = current_price - spread / 2
            ask = current_price + spread / 2
            
            # Estimate sizes
            bid_size = int(volume * 0.15)
            ask_size = int(volume * 0.15)
            
            # Occasionally create large orders
            if i % 7 == 0:  # Every 7th quote has a large order
                bid_size = int(bid_size * 3)  # Large buy order
            elif i % 11 == 0:  # Every 11th quote
                ask_size = int(ask_size * 3)  # Large sell order
            
            timestamp = base_time + timedelta(minutes=i)
            
            quote = {
                'symbol': symbol,
                'bid': round(bid, 2),
                'ask': round(ask, 2),
                'bid_size': bid_size,
                'ask_size': ask_size,
                'last': current_price,
                'volume': volume,
                'timestamp': timestamp.isoformat(),
                'open': current_price - 0.1,
                'high': current_price + 0.2,
                'low': current_price - 0.2,
                'close': current_price,
            }
            quotes.append(quote)
        
        logger.info(f"✅ Created {len(quotes)} sample quotes for testing")
        logger.info("")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"🧪 SIMULATING LIVE STREAM - {symbol}")
    logger.info("=" * 80)
    logger.info(f"📊 Processing {len(quotes)} historical quotes as live stream")
    logger.info(f"📅 Data from: {quotes[0].get('timestamp', 'N/A')}")
    logger.info("")
    
    # Initialize streamer components
    order_tracker = LargeOrderTracker(min_order_value=50000.0)
    trade_tracker = LargeTradeTracker(min_trade_value=50000.0)
    db = get_db()
    notification_service = get_notification_service()
    
    if db:
        db.connect()
    
    # Statistics
    total_orders_detected = 0
    total_trades_detected = 0
    total_notifications_sent = 0
    
    # Process each quote as if it were live
    logger.info("📈 STREAMING ACTIVE - Processing quotes...")
    logger.info("")
    
    for i, quote in enumerate(quotes, 1):
        timestamp = quote.get('timestamp', '')
        symbol = quote.get('symbol', 'N/A')
        price = quote.get('last', 0)
        volume = quote.get('volume', 0)
        
        logger.info(f"[{i}/{len(quotes)}] Processing quote: {symbol} @ ${price:.2f} | Vol: {volume:,}")
        
        # Process through order tracker and trade tracker
        detected = process_quote_through_streamer(
            quote, order_tracker, trade_tracker, db, notification_service
        )
        
        for item_type, item_data in detected:
            if item_type == 'order':
                total_orders_detected += 1
            elif item_type == 'trade':
                total_trades_detected += 1
        
        # Simulate order book scanning (every 5th quote)
        if i % 5 == 0:
            bids, asks = simulate_order_book_from_quote(quote)
            book_time = quote.get('timestamp', datetime.now(timezone.utc).isoformat())
            
            detected_book_orders = process_order_book_through_streamer(
                symbol, bids, asks, book_time, 'NASDAQ', db, notification_service, scan_all_orders=False
            )
            total_orders_detected += len(detected_book_orders)
        
        # Small delay to simulate real-time
        await asyncio.sleep(0.1)
    
    # Final statistics
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 STREAM SIMULATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"   Quotes processed: {len(quotes)}")
    logger.info(f"   Orders detected: {total_orders_detected}")
    logger.info(f"   Trades detected: {total_trades_detected}")
    
    order_stats = order_tracker.get_stats()
    trade_stats = trade_tracker.get_stats()
    logger.info(f"   Order tracker: {order_stats['orders_detected']} detected, {order_stats['duplicates_ignored']} duplicates ignored")
    logger.info(f"   Trade tracker: {trade_stats['trades_tracked']} tracked")
    logger.info("=" * 80)
    logger.info("")
    
    if db:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test streamer with real historical data from Schwab API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_real_stream.py NVDA 30
  python3 test_real_stream.py NVDA 50 --yesterday
  python3 test_real_stream.py AAPL 30 --days 2
        """
    )
    
    parser.add_argument(
        'symbol',
        type=str,
        help='Symbol to test (e.g., NVDA, AAPL)'
    )
    parser.add_argument(
        'limit',
        type=int,
        nargs='?',
        default=30,
        help='Number of historical periods to fetch (default: 30)'
    )
    parser.add_argument(
        '--yesterday',
        action='store_true',
        help='Use yesterday\'s data (default: 1 day back)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Days back to fetch data (default: 1)'
    )
    
    args = parser.parse_args()
    
    days_back = args.days
    if args.yesterday:
        days_back = 1
    
    asyncio.run(simulate_live_stream(
        symbol=args.symbol.upper(),
        limit=args.limit,
        days_back=days_back
    ))


if __name__ == "__main__":
    main()

