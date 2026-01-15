"""
Bot Trader - Main Streaming Bot
================================

This is THE main bot script. Run this to start everything.

Features (all enabled by default):
  - S&P 500 streaming (real-time market data)
  - Large trade tracking (>= $200k, saves to order_flow table)
  - Email notifications (for large trades only, to alert_recipients table)

Usage:
  python3 schwab_streamer.py

This is the single source of truth - all logic is here.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Import database module
try:
    from db import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logging.warning("Database module not available - quotes will be buffered only")

# Import notification module
try:
    from notifications import get_notification_service
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logging.warning("Notifications module not available - emails will not be sent")

# Import trade tracker module
try:
    from trade_tracker import LargeTradeTracker
    TRADE_TRACKER_AVAILABLE = True
except ImportError:
    TRADE_TRACKER_AVAILABLE = False
    logging.warning("Trade tracker module not available - large trades will not be tracked")

# Import order tracker module
try:
    from order_tracker import LargeOrderTracker
    ORDER_TRACKER_AVAILABLE = True
except ImportError:
    ORDER_TRACKER_AVAILABLE = False
    logging.warning("Order tracker module not available - large orders will not be tracked")

# Configure verbose logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Schwab API credentials
SCHWAB_APP_KEY = os.getenv("SCHWAB_APP_KEY")
SCHWAB_APP_SECRET = os.getenv("SCHWAB_APP_SECRET")
SCHWAB_CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "http://127.0.0.1:8080")
TOKEN_PATH = Path("token.json")

# S&P 500 symbols (full list - top 100 for initial deployment, can expand)
SP500_SYMBOLS = [
    'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'BRK.B', 'V',
    'UNH', 'JNJ', 'WMT', 'XOM', 'JPM', 'MA', 'PG', 'LLY', 'AVGO', 'CVX',
    'HD', 'MRK', 'COST', 'ABBV', 'ADBE', 'PEP', 'TMO', 'CSCO', 'MCD', 'ABT',
    'NFLX', 'ACN', 'LIN', 'NKE', 'CRM', 'AMD', 'DIS', 'WFC', 'VZ', 'DHR',
    'BMY', 'PM', 'TXN', 'RTX', 'CMCSA', 'UPS', 'NEE', 'AMGN', 'QCOM', 'COP',
    'INTU', 'HON', 'AMAT', 'SPGI', 'LOW', 'ADP', 'AXP', 'BKNG', 'T', 'ELV',
    'DE', 'GE', 'SBUX', 'GS', 'AMT', 'MU', 'TJX', 'MDT', 'BLK', 'ETN',
    'ZTS', 'CB', 'SCHW', 'PNC', 'C', 'MS', 'CAT', 'MO', 'CI', 'SO',
    'FI', 'ICE', 'WM', 'CL', 'EQIX', 'SLB', 'APD', 'AON', 'EMR', 'FIS',
    'PSA', 'ITW', 'SHW', 'CME', 'NOC', 'GD', 'APH', 'KLAC', 'MCO', 'FTNT',
]


class SchwabStreamer:
    """
    Main Bot - Streaming Trader
    
    This is the main bot class. Tracks large trades (>= $200k) only:
    - S&P 500 streaming (background processing)
    - Large trade detection and tracking
    - Database persistence (order_flow table)
    - Email notifications (for large trades only)
    """
    
    def __init__(self, symbols=None):
        self.app_key = SCHWAB_APP_KEY
        self.app_secret = SCHWAB_APP_SECRET
        self.callback_url = SCHWAB_CALLBACK_URL
        self.token_path = TOKEN_PATH
        self.client = None
        self.stream_client = None
        self.running = False
        self.symbols = symbols or SP500_SYMBOLS
        self.message_count = 0
        self.quote_count = {}
        self.db = get_db() if DB_AVAILABLE else None
        self.notification_service = get_notification_service() if NOTIFICATIONS_AVAILABLE else None
        self.trade_tracker = LargeTradeTracker(min_trade_value=50000.0) if TRADE_TRACKER_AVAILABLE else None
        self.order_tracker = LargeOrderTracker(min_order_value=50000.0) if ORDER_TRACKER_AVAILABLE else None
        self.notifications_sent = 0
        self.large_trades_saved = 0
        self.large_orders_saved = 0
        self.all_orders_saved = 0
        
        # Configuration: Scan ALL orders or just large ones?
        # Set to True to scan and save EVERY order from the order book
        self.scan_all_orders = os.getenv("SCAN_ALL_ORDERS", "false").lower() == "true"
        
    def authenticate(self) -> bool:
        """
        Authenticate with Schwab API.
        
        For production (AWS/cloud), token should be provided via SCHWAB_TOKEN_JSON env var.
        For local development, token.json file is used, or OAuth flow will start.
        """
        try:
            from schwab.auth import easy_client, client_from_token_file
            import json
            
            if not self.app_key or not self.app_secret:
                logger.error("SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set")
                return False
            
            # Check if we're in production (AWS/GCP/cloud environment)
            is_production = (
                os.getenv("AWS_EXECUTION_ENV") or  # AWS Lambda
                os.getenv("ECS_CONTAINER_METADATA_URI") or  # AWS ECS
                os.getenv("EC2_INSTANCE_ID") or  # AWS EC2
                os.getenv("GOOGLE_CLOUD_PROJECT") or  # Google Cloud
                os.getenv("GCE_INSTANCE") or  # Google Compute Engine
                os.getenv("PRODUCTION") == "true"
            )
            
            # In production, check for token in environment variable first
            token_json_env = os.getenv("SCHWAB_TOKEN_JSON")
            if token_json_env:
                try:
                    logger.info("Loading token from SCHWAB_TOKEN_JSON environment variable...")
                    # Parse and write token to file temporarily
                    token_data = json.loads(token_json_env)
                    self.token_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.token_path, 'w') as f:
                        json.dump(token_data, f)
                    logger.info(f"Token written to {self.token_path}")
                except Exception as e:
                    logger.error(f"Failed to parse SCHWAB_TOKEN_JSON: {e}")
                    return False
            
            # Try to load existing token (from env var or local file)
            if self.token_path.exists():
                try:
                    logger.info("Loading client from existing token...")
                    self.client = client_from_token_file(
                        token_path=str(self.token_path),
                        app_secret=self.app_secret,
                        api_key=self.app_key,
                    )
                    logger.info("✅ Authenticated with existing token")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to load token: {e}")
                    if is_production:
                        logger.error("Cannot perform OAuth in production. Please provide valid SCHWAB_TOKEN_JSON.")
                        return False
                    logger.info("Starting OAuth flow...")
            
            # No valid token - start OAuth flow (only in local development)
            if is_production:
                logger.error("OAuth flow not available in production.")
                logger.error("Please create token.json locally and set SCHWAB_TOKEN_JSON environment variable.")
                return False
            
            logger.info("Starting OAuth authorization...")
            logger.info(f"Using callback URL: {self.callback_url}")
            
            # Verify callback URL has a port (required for schwab-py)
            if self.callback_url and ':' in self.callback_url:
                # Extract host:port to verify
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(self.callback_url)
                    if parsed.port is None:
                        logger.error(f"Callback URL must include a port number: {self.callback_url}")
                        logger.error("Example: http://127.0.0.1:8080 or https://127.0.0.1:8080")
                        return False
                    logger.info(f"Callback URL verified - Host: {parsed.hostname}, Port: {parsed.port}")
                except Exception as e:
                    logger.warning(f"Could not parse callback URL: {e}")
            
            try:
                self.client = easy_client(
                    api_key=self.app_key,
                    app_secret=self.app_secret,
                    callback_url=self.callback_url,
                    token_path=str(self.token_path),
                    asyncio=False,
                    interactive=True,
                )
            except Exception as oauth_error:
                logger.error(f"OAuth failed: {oauth_error}")
                if "port" in str(oauth_error).lower():
                    logger.error("")
                    logger.error("⚠️  PORTAL CALLBACK URL MUST MATCH EXACTLY!")
                    logger.error(f"   Portal should have: {self.callback_url}")
                    logger.error(f"   Your .env has: {self.callback_url}")
                    logger.error("")
                    logger.error("If using HTTPS, your browser will show a security warning.")
                    logger.error("Click 'Advanced' → 'Proceed to 127.0.0.1 (unsafe)' when prompted.")
                    logger.error("This is normal and safe for localhost OAuth.")
                raise
            logger.info("✅ OAuth authorization successful!")
            return True
            
        except ImportError:
            logger.error("schwab-py not installed. Run: pip install schwab-py")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}", exc_info=True)
            return False
    
    def process_order_book(self, msg):
        """Process incoming order book data - scan ALL orders at each price level"""
        try:
            # Parse message structure
            if isinstance(msg, dict):
                service = msg.get('service', '')
                
                # Handle NASDAQ order book
                if service == 'NASDAQ_BOOK':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('0', ''))  # BookFields.SYMBOL = 0
                            bids = item.get('1', [])  # BookFields.BIDS = 1
                            asks = item.get('2', [])  # BookFields.ASKS = 2
                            book_time = item.get('3', None)  # BookFields.BOOK_TIME = 3
                            
                            self.scan_order_book(symbol, bids, asks, book_time, 'NASDAQ')
                
                # Handle NYSE order book
                elif service == 'NYSE_BOOK':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('0', ''))
                            bids = item.get('1', [])
                            asks = item.get('2', [])
                            book_time = item.get('3', None)
                            
                            self.scan_order_book(symbol, bids, asks, book_time, 'NYSE')
                
                # Handle Options order book
                elif service == 'OPTIONS_BOOK':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('0', ''))
                            bids = item.get('1', [])
                            asks = item.get('2', [])
                            book_time = item.get('3', None)
                            
                            self.scan_order_book(symbol, bids, asks, book_time, 'OPTIONS')
                            
        except Exception as e:
            logger.error(f"Error processing order book: {e}", exc_info=True)
    
    def scan_order_book(self, symbol: str, bids: list, asks: list, book_time, exchange: str):
        """
        Scan order book to find ALL orders at each price level
        
        If SCAN_ALL_ORDERS=true, saves EVERY order (regardless of size).
        Otherwise, only saves large orders (>= $50k).
        
        Args:
            symbol: Stock/option symbol
            bids: List of bid orders [{'price': X, 'size': Y}, ...]
            asks: List of ask orders [{'price': X, 'size': Y}, ...]
            book_time: Timestamp of order book snapshot
            exchange: Exchange name (NASDAQ, NYSE, OPTIONS)
        """
        if not symbol:
            return
        
        # Handle empty bid/ask lists
        bids = bids or []
        asks = asks or []
        
        try:
            orders_scanned = 0
            orders_saved = 0
            
            # Scan all bid orders (buy orders)
            for bid_order in bids:
                if isinstance(bid_order, dict):
                    price = bid_order.get('price')
                    size = bid_order.get('size', bid_order.get('quantity', 0))
                    
                    if price and size:
                        try:
                            price_float = float(price)
                            size_int = int(size)
                            order_value = price_float * size_int
                            orders_scanned += 1
                            
                            # Create order data
                            order_data = {
                                'symbol': symbol,
                                'order_type': 'BUY_ORDER',
                                'order_side': 'BUY',
                                'order_value_usd': order_value,
                                'price': price_float,
                                'order_size_shares': size_int,
                                'timestamp': datetime.now(timezone.utc),
                                'instrument': 'equity' if exchange != 'OPTIONS' else 'option',
                                'detection_method': 'ORDER_BOOK_BID',
                                'exchange': exchange,
                                'book_time': book_time,
                                'price_level': 'BID',
                            }
                            
                            # Determine if we should save this order
                            should_save = False
                            is_large = order_value >= (self.order_tracker.min_order_value if self.order_tracker else 50000.0)
                            
                            if self.scan_all_orders:
                                # Save ALL orders when scan_all_orders is enabled
                                should_save = True
                            elif is_large:
                                # Save only large orders when scan_all_orders is disabled
                                should_save = True
                            
                            if should_save and self.db:
                                if self.scan_all_orders:
                                    # Save all orders using save_all_order
                                    if self.db.save_all_order(order_data):
                                        orders_saved += 1
                                        self.all_orders_saved += 1
                                else:
                                    # Save large orders using save_large_order
                                    if self.db.save_large_order(order_data):
                                        orders_saved += 1
                                        self.large_orders_saved += 1
                                        logger.info(
                                            f"📋 Large BUY order in book: {symbol} | "
                                            f"Value: ${order_value:,.2f} | "
                                            f"Size: {size_int:,} @ ${price_float:.2f} | "
                                            f"Exchange: {exchange}"
                                        )
                                        
                                        # Send notification for large orders only
                                        if self.notification_service:
                                            sent = self.notification_service.send_order_notification(order_data)
                                            if sent > 0:
                                                self.notifications_sent += sent
                        except (ValueError, TypeError) as e:
                            continue
            
            # Scan all ask orders (sell orders)
            for ask_order in asks:
                if isinstance(ask_order, dict):
                    price = ask_order.get('price')
                    size = ask_order.get('size', ask_order.get('quantity', 0))
                    
                    if price and size:
                        try:
                            price_float = float(price)
                            size_int = int(size)
                            order_value = price_float * size_int
                            orders_scanned += 1
                            
                            # Create order data
                            order_data = {
                                'symbol': symbol,
                                'order_type': 'SELL_ORDER',
                                'order_side': 'SELL',
                                'order_value_usd': order_value,
                                'price': price_float,
                                'order_size_shares': size_int,
                                'timestamp': datetime.now(timezone.utc),
                                'instrument': 'equity' if exchange != 'OPTIONS' else 'option',
                                'detection_method': 'ORDER_BOOK_ASK',
                                'exchange': exchange,
                                'book_time': book_time,
                                'price_level': 'ASK',
                            }
                            
                            # Determine if we should save this order
                            should_save = False
                            is_large = order_value >= (self.order_tracker.min_order_value if self.order_tracker else 50000.0)
                            
                            if self.scan_all_orders:
                                # Save ALL orders when scan_all_orders is enabled
                                should_save = True
                            elif is_large:
                                # Save only large orders when scan_all_orders is disabled
                                should_save = True
                            
                            if should_save and self.db:
                                if self.scan_all_orders:
                                    # Save all orders using save_all_order
                                    if self.db.save_all_order(order_data):
                                        orders_saved += 1
                                        self.all_orders_saved += 1
                                else:
                                    # Save large orders using save_large_order
                                    if self.db.save_large_order(order_data):
                                        orders_saved += 1
                                        self.large_orders_saved += 1
                                        logger.info(
                                            f"📋 Large SELL order in book: {symbol} | "
                                            f"Value: ${order_value:,.2f} | "
                                            f"Size: {size_int:,} @ ${price_float:.2f} | "
                                            f"Exchange: {exchange}"
                                        )
                                        
                                        # Send notification for large orders only
                                        if self.notification_service:
                                            sent = self.notification_service.send_order_notification(order_data)
                                            if sent > 0:
                                                self.notifications_sent += sent
                        except (ValueError, TypeError) as e:
                            continue
            
            # Log summary if scanning all orders
            if self.scan_all_orders and orders_scanned > 0:
                logger.debug(
                    f"📊 Order book scan: {symbol} | "
                    f"Scanned: {orders_scanned} orders | "
                    f"Saved: {orders_saved} orders | "
                    f"Exchange: {exchange}"
                )
                            
        except Exception as e:
            logger.error(f"Error scanning order book for {symbol}: {e}", exc_info=True)
    
    def process_quote(self, msg):
        """Process incoming quote data - track large trades only"""
        try:
            self.message_count += 1
            
            # Parse message structure
            if isinstance(msg, dict):
                service = msg.get('service', '')
                if service == 'LEVELONE_EQUITIES':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('1', ''))
                            
                            # Extract quote data
                            bid = item.get('2', None)
                            ask = item.get('3', None)
                            last = item.get('4', None)
                            bid_size = item.get('5', None)
                            ask_size = item.get('6', None)
                            volume = item.get('8', None)
                            
                            # Track quotes per symbol
                            if symbol not in self.quote_count:
                                self.quote_count[symbol] = 0
                            self.quote_count[symbol] += 1
                            
                            # Create quote data structure for trade tracking
                            quote_data = {
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'symbol': symbol,
                                'bid': bid,
                                'ask': ask,
                                'last': last,
                                'bid_size': bid_size,
                                'ask_size': ask_size,
                                'volume': volume,
                            }
                            
                            # Track large orders (>= $50k) - Enhanced multi-signal detection
                            if self.order_tracker:
                                large_order = self.order_tracker.process_quote(quote_data)
                                if large_order:
                                    # Save large order to database
                                    if self.db and self.db.save_large_order(large_order):
                                        self.large_orders_saved += 1
                                        
                                        # Get detection method for logging
                                        detection_method = large_order.get('detection_method', 'UNKNOWN')
                                        
                                        logger.info(
                                            f"📋 Large {large_order.get('order_type')} order detected ({detection_method}): {symbol} | "
                                            f"Value: ${large_order.get('order_value_usd', 0):,.2f} | "
                                            f"Size: {large_order.get('order_size_shares', 0):,} shares @ ${large_order.get('price')} | "
                                            f"Instrument: {large_order.get('instrument', 'equity')}"
                                        )
                                        
                                        # Send email notification for large orders
                                        if self.notification_service:
                                            sent = self.notification_service.send_order_notification(large_order)
                                            if sent > 0:
                                                self.notifications_sent += sent
                            
                            # Track large trades (>= $50k) - Enhanced volume spike detection
                            if self.trade_tracker:
                                large_trade = self.trade_tracker.process_quote(quote_data)
                                if large_trade:
                                    # Save large trade to database
                                    if self.db and self.db.save_large_trade(large_trade):
                                        self.large_trades_saved += 1
                                        
                                        # Get detection method for logging
                                        detection_method = large_trade.get('detection_method', 'UNKNOWN')
                                        
                                        logger.info(
                                            f"💰 Large trade detected ({detection_method}): {symbol} | "
                                            f"Value: ${large_trade.get('trade_value_usd', 0):,.2f} | "
                                            f"Entry: ${large_trade.get('entry_price')} → Exit: ${large_trade.get('exit_price')} | "
                                            f"Vol: {large_trade.get('volume', 0):,}"
                                        )
                                        
                                        # Send email notification for large trades
                                        if self.notification_service:
                                            sent = self.notification_service.send_large_trade_notification(large_trade)
                                            if sent > 0:
                                                self.notifications_sent += sent
                            
                            # Log status every 100 messages (minimal logging)
                            if self.message_count % 100 == 0:
                                if self.scan_all_orders:
                                    status_msg = (
                                        f"📈 Status: {self.message_count} messages processed | "
                                        f"All orders saved: {self.all_orders_saved} | "
                                        f"Large trades: {self.large_trades_saved} | "
                                        f"Symbols tracked: {len(self.quote_count)}"
                                    )
                                else:
                                    status_msg = (
                                        f"📈 Status: {self.message_count} messages processed | "
                                        f"Large orders: {self.large_orders_saved} | "
                                        f"Large trades: {self.large_trades_saved} | "
                                        f"Symbols tracked: {len(self.quote_count)}"
                                    )
                                logger.info(status_msg)
        except Exception as e:
            logger.warning(f"⚠️  Error processing quote: {e}")
            logger.debug(f"Raw message: {msg}")
    
    async def start_streaming_async(self):
        """Start streaming S&P 500 market data (async version)"""
        if not self.client:
            logger.error("Not authenticated. Call authenticate() first.")
            return
        
        try:
            from schwab.streaming import StreamClient
            
            logger.info("=" * 80)
            logger.info("📊 S&P 500 SCANNER - STARTING")
            logger.info("=" * 80)
            logger.info(f"📋 Configuration:")
            logger.info(f"   Symbols: {len(self.symbols)} stocks")
            logger.info(f"   Mode: Real-time Level 1 quotes + Order Book (Level 2)")
            logger.info(f"   Session: NY market hours (9:30 AM - 4:00 PM ET)")
            logger.info(f"   Symbols: {', '.join(self.symbols[:10])}..." if len(self.symbols) > 10 else f"   Symbols: {', '.join(self.symbols)}")
            logger.info("")
            
            # Initialize database (for large trades only)
            if self.db:
                logger.info("💾 Initializing database connection...")
                if self.db.connect():
                    logger.info("✅ Database ready (for large trade tracking)")
                else:
                    logger.warning("⚠️  Database connection failed - large trades will not be saved")
            else:
                logger.warning("⚠️  Database not configured - large trades will not be saved")
            
            # Initialize notifications (for large trades only)
            if self.notification_service:
                recipients = self.notification_service.get_alert_recipients(use_cache=False)
                if recipients:
                    logger.info(f"📧 Email notifications enabled - {len(recipients)} recipient(s) (for large trades only)")
                else:
                    logger.info("📧 Email notifications configured but no recipients found in alert_recipients table")
            else:
                logger.info("📧 Email notifications not configured - GMAIL_USER and GMAIL_PASSWORD required")
            
            # Initialize order tracker
            if self.order_tracker:
                logger.info(f"📋 Large order tracking enabled (>= ${self.order_tracker.min_order_value:,.0f})")
                logger.info(f"   Tracks: Stocks and Options contracts")
            else:
                logger.warning("⚠️  Order tracker not available - large orders will not be tracked")
            
            # Initialize trade tracker
            if self.trade_tracker:
                logger.info(f"💰 Large trade tracking enabled (>= ${self.trade_tracker.min_trade_value:,.0f})")
            else:
                logger.warning("⚠️  Trade tracker not available - large trades will not be tracked")
            
            logger.info("")
            
            # Initialize stream client
            self.stream_client = StreamClient(
                client=self.client,
                account_id=None,  # Not needed for market data
                enforce_enums=False,  # Allow integer field IDs instead of enum types
            )
            
            logger.info("🔌 Initializing stream client...")
            self.running = True
            
            # Register message handlers
            self.stream_client.add_level_one_equity_handler(self.process_quote)
            
            # Register order book handlers (Level 2 - full order book data)
            self.stream_client.add_nasdaq_book_handler(self.process_order_book)
            self.stream_client.add_nyse_book_handler(self.process_order_book)
            self.stream_client.add_options_book_handler(self.process_order_book)
            
            logger.info("✅ Message handlers registered (Level 1 + Order Book)")
            
            # Log scanning mode
            if self.scan_all_orders:
                logger.info("🔍 Mode: Scanning ALL orders from order book (every order will be saved)")
            else:
                logger.info("🔍 Mode: Scanning LARGE orders only (>= $50k)")
            
            # Login to stream
            logger.info("🔐 Connecting to Schwab streaming API...")
            await self.stream_client.login()
            logger.info("✅ Stream connected successfully")
            logger.info("")
            
            # Subscribe to S&P 500 symbols with fields
            # Fields: 0=Symbol, 1=Bid, 2=Ask, 3=Last, 4=Bid Size, 5=Ask Size, 8=Total Volume
            logger.info(f"📡 Subscribing to {len(self.symbols)} symbols...")
            
            # Subscribe in batches (API may have limits)
            batch_size = 100
            for i in range(0, len(self.symbols), batch_size):
                batch = self.symbols[i:i+batch_size]
                
                # Subscribe to Level 1 quotes (top of book)
                await self.stream_client.level_one_equity_subs(
                    symbols=batch,
                    fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
                )
                
                # Subscribe to order book (Level 2 - ALL orders at each price level)
                # This gives us EVERY order, not just top bid/ask
                try:
                    # Try NASDAQ book first (most stocks are NASDAQ)
                    await self.stream_client.nasdaq_book_subs(symbols=batch)
                    logger.info(f"   ✅ Subscribed Level 1 + Order Book for batch {i//batch_size + 1} ({len(batch)} symbols)")
                except Exception as e:
                    # If NASDAQ fails, try NYSE
                    try:
                        await self.stream_client.nyse_book_subs(symbols=batch)
                        logger.info(f"   ✅ Subscribed Level 1 + Order Book (NYSE) for batch {i//batch_size + 1} ({len(batch)} symbols)")
                    except Exception as e2:
                        logger.warning(f"   ⚠️  Order book subscription failed for batch {i//batch_size + 1}: {e2}")
                        logger.info(f"   ✅ Subscribed Level 1 only for batch {i//batch_size + 1} ({len(batch)} symbols)")
                
                if i + batch_size < len(self.symbols):
                    await asyncio.sleep(0.5)  # Small delay between batches
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Subscribed to all {len(self.symbols)} symbols")
            logger.info("   📊 Level 1: Top bid/ask quotes")
            logger.info("   📚 Order Book: ALL orders at each price level")
            logger.info("=" * 80)
            logger.info("📈 STREAMING ACTIVE - Scanning EVERY order in real-time")
            logger.info("   Press Ctrl+C to stop")
            logger.info("")
            
            # Handle messages in a loop with infinite reconnection logic
            reconnect_delay = 5  # seconds
            reconnect_attempts = 0
            last_message_time = datetime.now(timezone.utc)
            last_connection_time = datetime.now(timezone.utc)
            
            while self.running:
                try:
                    await self.stream_client.handle_message()
                    # Reset reconnect attempts on successful message
                    reconnect_attempts = 0
                    last_message_time = datetime.now(timezone.utc)
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    # Check if it's a connection error
                    if "ConnectionClosed" in error_type or "IncompleteRead" in error_type or "WebSocket" in error_type:
                        reconnect_attempts += 1
                        
                        # Calculate time since last message to diagnose idle timeout
                        time_since_last_msg = (datetime.now(timezone.utc) - last_message_time).total_seconds()
                        time_since_connection = (datetime.now(timezone.utc) - last_connection_time).total_seconds()
                        
                        # Log diagnostic information
                        logger.warning("=" * 80)
                        logger.warning(f"⚠️  CONNECTION DROPPED - Diagnostic Info:")
                        logger.warning(f"   Error Type: {error_type}")
                        logger.warning(f"   Error Message: {error_msg}")
                        logger.warning(f"   Time since last message: {time_since_last_msg:.1f} seconds ({time_since_last_msg/60:.1f} minutes)")
                        logger.warning(f"   Time since connection: {time_since_connection:.1f} seconds ({time_since_connection/60:.1f} minutes)")
                        
                        if time_since_last_msg > 1800:  # 30 minutes
                            logger.warning(f"   🔍 Likely cause: IDLE TIMEOUT (>30 min without data)")
                        elif time_since_last_msg > 300:  # 5 minutes
                            logger.warning(f"   🔍 Possible cause: Idle connection (no data for {time_since_last_msg/60:.1f} min)")
                        else:
                            logger.warning(f"   🔍 Likely cause: Network/server issue (was receiving data)")
                        
                        logger.warning(f"   Reconnect attempt: {reconnect_attempts} (unlimited)")
                        logger.warning("=" * 80)
                        
                        # Clean up old connection
                        if self.stream_client:
                            try:
                                await self.stream_client.logout()
                            except:
                                pass
                        
                        # Exponential backoff: 5s, 10s, 20s, 30s, then 30s max
                        backoff_delay = min(reconnect_delay * (2 ** min(reconnect_attempts - 1, 3)), 30)
                        logger.info(f"⏳ Waiting {backoff_delay} seconds before reconnect...")
                        await asyncio.sleep(backoff_delay)
                        
                        try:
                            # Reinitialize stream client
                            self.stream_client = StreamClient(
                                client=self.client,
                                account_id=None,
                                enforce_enums=False,
                            )
                            
                            # Re-register message handler
                            self.stream_client.add_level_one_equity_handler(self.process_quote)
                            
                            # Re-login
                            logger.info("🔄 Reconnecting to stream...")
                            await self.stream_client.login()
                            logger.info("✅ Reconnected successfully")
                            last_connection_time = datetime.now(timezone.utc)
                            
                            # Re-subscribe to all symbols (Level 1 + Order Book)
                            logger.info(f"📡 Re-subscribing to {len(self.symbols)} symbols...")
                            batch_size = 100
                            for i in range(0, len(self.symbols), batch_size):
                                batch = self.symbols[i:i+batch_size]
                                
                                # Re-subscribe to Level 1
                                await self.stream_client.level_one_equity_subs(
                                    symbols=batch,
                                    fields=[0, 1, 2, 3, 4, 5, 6, 8]
                                )
                                
                                # Re-subscribe to order book
                                try:
                                    await self.stream_client.nasdaq_book_subs(symbols=batch)
                                except:
                                    try:
                                        await self.stream_client.nyse_book_subs(symbols=batch)
                                    except:
                                        pass  # Order book may not be available for all symbols
                                
                                if i + batch_size < len(self.symbols):
                                    await asyncio.sleep(0.5)
                            
                            logger.info("✅ Re-subscription complete - Resuming stream...")
                            # Continue loop to handle messages
                            continue
                            
                        except Exception as reconnect_error:
                            logger.error(f"❌ Reconnection failed: {reconnect_error}")
                            logger.error(f"   Will retry in {backoff_delay} seconds...")
                            # Continue loop to retry (infinite retries)
                            continue
                    else:
                        # Other errors - log and continue if possible
                        logger.warning(f"⚠️  Streaming error (non-connection): {e}")
                        # Small delay before continuing to avoid tight error loop
                        await asyncio.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Stream interrupted by user")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Fatal streaming error: {e}", exc_info=True)
            self.running = False
        finally:
            # Clean up on exit
            if self.stream_client:
                try:
                    await self.stream_client.logout()
                    logger.info("✅ Stream disconnected cleanly")
                except:
                    pass
    
    def start_streaming(self):
        """Start streaming market data (sync wrapper)"""
        try:
            asyncio.run(self.start_streaming_async())
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
            self.running = False
    
    async def stop_async(self):
        """Stop streaming (async)"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🛑 STOPPING BOT TRADER")
        logger.info("=" * 80)
        
        logger.info(f"📊 Summary:")
        logger.info(f"   Total messages processed: {self.message_count}")
        logger.info(f"   Large trades detected (>= $200k): {self.large_trades_saved}")
        logger.info(f"   Email notifications sent: {self.notifications_sent}")
        logger.info(f"   Symbols tracked: {len(self.quote_count)}")
        
        # Trade tracker stats
        if self.trade_tracker:
            tracker_stats = self.trade_tracker.get_stats()
            logger.info(f"   Trade tracker: {tracker_stats.get('trades_tracked')} trades detected")
        if self.quote_count:
            top_symbols = sorted(self.quote_count.items(), key=lambda x: x[1], reverse=True)[:10]
            logger.info(f"   Top symbols by quote count:")
            for symbol, count in top_symbols:
                logger.info(f"      {symbol:6}: {count} quotes")
        logger.info("")
        
        self.running = False
        if self.stream_client:
            try:
                logger.info("📴 Disconnecting from stream...")
                await self.stream_client.logout()
                logger.info("✅ Stream disconnected successfully")
            except Exception as e:
                logger.warning(f"⚠️  Error disconnecting stream: {e}")
        
        # Close database connection
        if self.db:
            self.db.close()
    
    def stop(self):
        """Stop streaming (sync wrapper)"""
        if self.stream_client:
            try:
                asyncio.run(self.stop_async())
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
                self.running = False


def main():
    """Main entry point - S&P 500 Scanner"""
    logger.info("🚀 Starting S&P 500 Scanner (Schwab Streamer)...")
    logger.info("")
    
    streamer = SchwabStreamer()
    
    if not streamer.authenticate():
        logger.error("❌ Authentication failed. Exiting.")
        sys.exit(1)
    
    try:
        streamer.start_streaming()
        
        # Keep running
        import time
        while streamer.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n")
        logger.info("🛑 Stopping scanner (KeyboardInterrupt)...")
        streamer.stop()
        logger.info("✅ Scanner stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

