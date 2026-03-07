"""
Bot Trader - Options Scanner
============================

This is THE main bot script. Run this to start everything.

Features (all enabled by default):
  - Options-only streaming (real-time market data)
  - Unusual volume detection (2x+ average volume)
  - Large order tracking (>= $50k, saves to order_flow table)
  - Large trade tracking (>= $50k, saves to order_flow table)
  - Email notifications (for large orders/trades and unusual volume)

Usage:
  python3 schwab_streamer.py

Set OPTIONS_SYMBOLS environment variable with comma-separated options symbols:
  OPTIONS_SYMBOLS=AAPL_240119C150,NVDA_240119C400,TSLA_240119P200

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

# Import unusual volume tracker module
try:
    from unusual_volume_tracker import UnusualVolumeTracker
    UNUSUAL_VOLUME_AVAILABLE = True
except ImportError:
    UNUSUAL_VOLUME_AVAILABLE = False
    logging.warning("Unusual volume tracker not available - unusual volume detection disabled")

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

# Options symbols - generate for popular underlyings
# Format: SYMBOL_YYMMDDC/P###.##
# Example: AAPL_240119C150 (AAPL Call, Jan 19 2024, $150 strike)

def generate_options_symbols(underlying_symbols, expiration_date, strikes):
    """
    Generate options symbols for Schwab API
    
    Format: SYMBOL_YYMMDDC/P###.##
    Example: AAPL_240119C150 (AAPL Call, Jan 19 2024, $150 strike)
    """
    options = []
    for symbol in underlying_symbols:
        for strike in strikes:
            # Call option
            call_symbol = f"{symbol}_{expiration_date}C{strike:.0f}"
            options.append(call_symbol)
            # Put option
            put_symbol = f"{symbol}_{expiration_date}P{strike:.0f}"
            options.append(put_symbol)
    return options

# Popular underlyings for options scanning
POPULAR_UNDERLYINGS = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'META', 'GOOGL', 'AMD', 'SPY', 'QQQ']

# Options symbols - can be set manually or generated dynamically
# For now, using placeholder - you'll need to populate with actual options symbols
# You can either:
# 1. Set manually: OPTIONS_SYMBOLS = ['AAPL_240119C150', 'NVDA_240119C400', ...]
# 2. Generate from active options chains (requires API call to get active strikes/expirations)
# 3. Use environment variable: OPTIONS_SYMBOLS env var (comma-separated)

OPTIONS_SYMBOLS = os.getenv("OPTIONS_SYMBOLS", "").split(",") if os.getenv("OPTIONS_SYMBOLS") else []

# If no options symbols provided, log warning
if not OPTIONS_SYMBOLS or (len(OPTIONS_SYMBOLS) == 1 and OPTIONS_SYMBOLS[0] == ""):
    OPTIONS_SYMBOLS = []
    logging.warning("⚠️  No OPTIONS_SYMBOLS configured. Set OPTIONS_SYMBOLS env var or populate in code.")
    logging.warning("   Example: OPTIONS_SYMBOLS=AAPL_240119C150,NVDA_240119C400,TSLA_240119P200")


class SchwabStreamer:
    """
    Main Bot - Options Scanner
    
    This is the main bot class. Scans OPTIONS ONLY:
    - Options streaming (real-time market data)
    - Unusual volume detection (2x+ average volume)
    - Large order detection and tracking (>= $50k)
    - Large trade detection and tracking (>= $50k)
    - Database persistence (order_flow table)
    - Email notifications (for large orders/trades and unusual volume)
    """
    
    def __init__(self, symbols=None):
        self.app_key = SCHWAB_APP_KEY
        self.app_secret = SCHWAB_APP_SECRET
        self.callback_url = SCHWAB_CALLBACK_URL
        self.token_path = TOKEN_PATH
        self.client = None
        self.stream_client = None
        self.running = False
        self.symbols = symbols or OPTIONS_SYMBOLS
        self.message_count = 0
        self.quote_count = {}
        self.db = get_db() if DB_AVAILABLE else None
        self.notification_service = get_notification_service() if NOTIFICATIONS_AVAILABLE else None
        self.trade_tracker = LargeTradeTracker(min_trade_value=50000.0) if TRADE_TRACKER_AVAILABLE else None
        self.order_tracker = LargeOrderTracker(min_order_value=50000.0) if ORDER_TRACKER_AVAILABLE else None
        self.unusual_volume_tracker = UnusualVolumeTracker(unusual_threshold=2.0) if UNUSUAL_VOLUME_AVAILABLE else None
        self.notifications_sent = 0
        self.large_trades_saved = 0
        self.large_orders_saved = 0
        self.all_orders_saved = 0
        self.unusual_volume_detections = 0
        
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
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse SCHWAB_TOKEN_JSON (invalid JSON): {e}")
                    logger.error("   SCHWAB_TOKEN_JSON should be a valid JSON string")
                    return False
                except Exception as e:
                    logger.error(f"Failed to write token from SCHWAB_TOKEN_JSON: {e}")
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
                    
                    # Don't test token here - let it fail during streaming if needed
                    # Testing here causes OAuth to trigger every time if refresh_token is expired
                    # Instead, let the streaming login handle it, which has better error messages
                    logger.info("✅ Token loaded (will validate during streaming)")
                    return True
                            
                except Exception as e:
                    error_str = str(e)
                    logger.warning(f"Failed to load token: {e}")
                    
                    # Check if it's a refresh token expiration error
                    if "refresh_token_authentication_error" in error_str or "refresh token" in error_str.lower():
                        logger.error("")
                        logger.error("=" * 80)
                        logger.error("❌ REFRESH TOKEN EXPIRED")
                        logger.error("=" * 80)
                        logger.error("")
                        logger.error("The refresh_token in your token is expired (~90 days of inactivity).")
                        logger.error("You need to refresh it ONCE with browser OAuth, then it works for 90 days.")
                        logger.error("")
                        if is_production:
                            logger.error("For production:")
                            logger.error("  1. Refresh token locally: python3 schwab_streamer.py")
                            logger.error("  2. Extract new token: python3 scripts/extract_token.py")
                            logger.error("  3. Update SCHWAB_TOKEN_JSON in your production environment")
                            logger.error("")
                        else:
                            logger.error("Solution:")
                            logger.error("  Run: python3 schwab_streamer.py")
                            logger.error("  → This will open browser for OAuth (one-time)")
                            logger.error("  → Complete authentication to get fresh refresh_token")
                            logger.error("  → After that, auto-refresh works for 90 days")
                            logger.error("")
                        logger.error("=" * 80)
                        logger.error("")
                    
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
                            
                            if should_save:
                                # Try to save to database (continue even if fails)
                                db_saved = False
                                if self.db:
                                    try:
                                        if self.scan_all_orders:
                                            if self.db.save_all_order(order_data):
                                                orders_saved += 1
                                                self.all_orders_saved += 1
                                                db_saved = True
                                        else:
                                            if self.db.save_large_order(order_data):
                                                orders_saved += 1
                                                self.large_orders_saved += 1
                                                db_saved = True
                                    except Exception as db_error:
                                        logger.warning(f"⚠️  Database save failed for order book order (continuing): {db_error}")
                                        # Continue - don't let DB failure stop streaming
                                
                                # Log large orders (always log, even if DB save failed)
                                if not self.scan_all_orders:
                                    logger.info(
                                        f"📋 Large BUY order in book: {symbol} | "
                                        f"Value: ${order_value:,.2f} | "
                                        f"Size: {size_int:,} @ ${price_float:.2f} | "
                                        f"Exchange: {exchange}"
                                        + ("" if db_saved else " | ⚠️ DB save failed")
                                    )
                                    
                                    # Send notification (always send, even if DB save failed)
                                    if self.notification_service:
                                        try:
                                            sent = self.notification_service.send_order_notification(order_data)
                                            if sent > 0:
                                                self.notifications_sent += sent
                                        except Exception as notif_error:
                                            logger.warning(f"⚠️  Notification send failed (continuing): {notif_error}")
                                            # Continue - don't let notification failure stop streaming
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
                            
                            if should_save:
                                # Try to save to database (continue even if fails)
                                db_saved = False
                                if self.db:
                                    try:
                                        if self.scan_all_orders:
                                            if self.db.save_all_order(order_data):
                                                orders_saved += 1
                                                self.all_orders_saved += 1
                                                db_saved = True
                                        else:
                                            if self.db.save_large_order(order_data):
                                                orders_saved += 1
                                                self.large_orders_saved += 1
                                                db_saved = True
                                    except Exception as db_error:
                                        logger.warning(f"⚠️  Database save failed for order book order (continuing): {db_error}")
                                        # Continue - don't let DB failure stop streaming
                                
                                # Log large orders (always log, even if DB save failed)
                                if not self.scan_all_orders:
                                    logger.info(
                                        f"📋 Large SELL order in book: {symbol} | "
                                        f"Value: ${order_value:,.2f} | "
                                        f"Size: {size_int:,} @ ${price_float:.2f} | "
                                        f"Exchange: {exchange}"
                                        + ("" if db_saved else " | ⚠️ DB save failed")
                                    )
                                    
                                    # Send notification (always send, even if DB save failed)
                                    if self.notification_service:
                                        try:
                                            sent = self.notification_service.send_order_notification(order_data)
                                            if sent > 0:
                                                self.notifications_sent += sent
                                        except Exception as notif_error:
                                            logger.warning(f"⚠️  Notification send failed (continuing): {notif_error}")
                                            # Continue - don't let notification failure stop streaming
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
        """Process incoming quote data - OPTIONS ONLY, track unusual volume and large orders/trades"""
        try:
            self.message_count += 1
            
            # Parse message structure
            if isinstance(msg, dict):
                service = msg.get('service', '')
                
                # Skip stock quotes - we only want options
                if service == 'LEVELONE_EQUITIES':
                    return
                
                # Only process options quotes
                if service == 'LEVELONE_OPTIONS':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('1', ''))
                            
                            # Extract quote data
                            # Level 1 Options fields: 0=Symbol, 1=Bid, 2=Ask, 3=Last, 4=Bid Size, 5=Ask Size, 6=High, 7=Low, 8=Volume, 9=Open Interest
                            bid = item.get('1', item.get('2', None))  # Field 1 = Bid
                            ask = item.get('2', item.get('3', None))  # Field 2 = Ask
                            last = item.get('3', item.get('4', None))  # Field 3 = Last
                            bid_size = item.get('4', item.get('5', None))  # Field 4 = Bid Size
                            ask_size = item.get('5', item.get('6', None))  # Field 5 = Ask Size
                            volume = item.get('8', None)  # Field 8 = Volume
                            open_interest = item.get('9', None)  # Field 9 = Open Interest (options only)
                            
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
                                'open_interest': open_interest,  # Open interest for options
                            }
                            
                            # Track large orders (>= $50k) - Enhanced multi-signal detection
                            if self.order_tracker:
                                large_order = self.order_tracker.process_quote(quote_data)
                                if large_order:
                                    # Get detection method for logging
                                    detection_method = large_order.get('detection_method', 'UNKNOWN')
                                    
                                    # Try to save large order to database (continue even if fails)
                                    db_saved = False
                                    if self.db:
                                        try:
                                            if self.db.save_large_order(large_order):
                                                self.large_orders_saved += 1
                                                db_saved = True
                                        except Exception as db_error:
                                            logger.warning(f"⚠️  Database save failed for order (continuing): {db_error}")
                                            # Continue - don't let DB failure stop streaming
                                    
                                    # Log detection (always log, even if DB save failed)
                                    logger.info(
                                        f"📋 Large {large_order.get('order_type')} order detected ({detection_method}): {symbol} | "
                                        f"Value: ${large_order.get('order_value_usd', 0):,.2f} | "
                                        f"Size: {large_order.get('order_size_shares', 0):,} shares @ ${large_order.get('price')} | "
                                        f"Instrument: {large_order.get('instrument', 'equity')}"
                                        + ("" if db_saved else " | ⚠️ DB save failed")
                                    )
                                    
                                    # Send email notification (always send, even if DB save failed)
                                    if self.notification_service:
                                        try:
                                            sent = self.notification_service.send_order_notification(large_order)
                                            if sent > 0:
                                                self.notifications_sent += sent
                                        except Exception as notif_error:
                                            logger.warning(f"⚠️  Notification send failed (continuing): {notif_error}")
                                            # Continue - don't let notification failure stop streaming
                            
                            # Track large trades (>= $50k) - Enhanced volume spike detection
                            if self.trade_tracker:
                                large_trade = self.trade_tracker.process_quote(quote_data)
                                if large_trade:
                                    # Get detection method for logging
                                    detection_method = large_trade.get('detection_method', 'UNKNOWN')
                                    
                                    # Try to save large trade to database (continue even if fails)
                                    db_saved = False
                                    if self.db:
                                        try:
                                            if self.db.save_large_trade(large_trade):
                                                self.large_trades_saved += 1
                                                db_saved = True
                                        except Exception as db_error:
                                            logger.warning(f"⚠️  Database save failed for trade (continuing): {db_error}")
                                            # Continue - don't let DB failure stop streaming
                                    
                                    # Log detection (always log, even if DB save failed)
                                    logger.info(
                                        f"💰 Large trade detected ({detection_method}): {symbol} | "
                                        f"Value: ${large_trade.get('trade_value_usd', 0):,.2f} | "
                                        f"Entry: ${large_trade.get('entry_price')} → Exit: ${large_trade.get('exit_price')} | "
                                        f"Vol: {large_trade.get('volume', 0):,}"
                                        + ("" if db_saved else " | ⚠️ DB save failed")
                                    )
                                    
                                    # Send email notification (always send, even if DB save failed)
                                    if self.notification_service:
                                        try:
                                            sent = self.notification_service.send_large_trade_notification(large_trade)
                                            if sent > 0:
                                                self.notifications_sent += sent
                                        except Exception as notif_error:
                                            logger.warning(f"⚠️  Notification send failed (continuing): {notif_error}")
                                            # Continue - don't let notification failure stop streaming
                            
                            # Track unusual volume in options
                            if self.unusual_volume_tracker:
                                unusual_volume = self.unusual_volume_tracker.process_quote(quote_data)
                                if unusual_volume:
                                    self.unusual_volume_detections += 1
                                    
                                    # Get details
                                    ratio = unusual_volume.get('volume_ratio', 0)
                                    option_type = unusual_volume.get('option_type', 'UNKNOWN')
                                    underlying = unusual_volume.get('underlying', 'UNKNOWN')
                                    current_vol = unusual_volume.get('current_volume', 0)
                                    avg_vol = unusual_volume.get('average_volume', 0)
                                    
                                    # Get quote data for reporting
                                    bid = quote_data.get('bid', 0)
                                    ask = quote_data.get('ask', 0)
                                    last = quote_data.get('last', 0)
                                    open_interest = quote_data.get('open_interest', 0)
                                    
                                    # Log unusual volume detection with full quote details
                                    logger.info(
                                        f"🚨 UNUSUAL VOLUME: {symbol} ({option_type}) | "
                                        f"Bid: ${bid:.2f} | Ask: ${ask:.2f} | Last: ${last:.2f} | "
                                        f"Volume: {current_vol:,} | Open Interest: {open_interest:,} | "
                                        f"Avg Vol: {avg_vol:,.0f} | Ratio: {ratio:.1f}x | "
                                        f"Underlying: {underlying}"
                                    )
                                    
                                    # Save to database
                                    if self.db:
                                        try:
                                            unusual_order = {
                                                'symbol': symbol,
                                                'order_type': 'UNUSUAL_VOLUME',
                                                'order_side': option_type,
                                                'order_value_usd': 0,  # Volume-based, not value-based
                                                'price': quote_data.get('last', 0),
                                                'order_size_shares': current_vol,
                                                'timestamp': datetime.now(timezone.utc),
                                                'instrument': 'option',
                                                'detection_method': 'UNUSUAL_VOLUME',
                                                'volume_ratio': ratio,
                                                'average_volume': avg_vol,
                                                'bid': bid,
                                                'ask': ask,
                                                'last': last,
                                                'volume': current_vol,
                                                'open_interest': open_interest,
                                                'underlying': underlying,
                                            }
                                            if self.db.save_large_order(unusual_order):
                                                logger.debug(f"💾 Saved unusual volume event to database: {symbol}")
                                        except Exception as db_error:
                                            logger.warning(f"⚠️  Database save failed for unusual volume (continuing): {db_error}")
                                    
                                    # Send notification
                                    if self.notification_service:
                                        try:
                                            # Create notification for unusual volume
                                            # For now, using order notification format
                                            # You may want to create a specific unusual_volume_notification method
                                            sent = self.notification_service.send_order_notification(unusual_order)
                                            if sent > 0:
                                                self.notifications_sent += sent
                                        except Exception as notif_error:
                                            logger.warning(f"⚠️  Unusual volume notification send failed (continuing): {notif_error}")
                            
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
                                        f"Unusual volume: {self.unusual_volume_detections} | "
                                        f"Contracts tracked: {len(self.quote_count)}"
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
            logger.info("📊 OPTIONS SCANNER - STARTING")
            logger.info("=" * 80)
            logger.info(f"📋 Configuration:")
            logger.info(f"   Contracts: {len(self.symbols)} options contracts")
            logger.info(f"   Mode: Real-time Options Level 1 quotes + Order Book (Level 2)")
            logger.info(f"   Session: NY market hours (9:30 AM - 4:00 PM ET)")
            if len(self.symbols) > 0:
                logger.info(f"   Sample: {', '.join(self.symbols[:5])}..." if len(self.symbols) > 5 else f"   Contracts: {', '.join(self.symbols)}")
            else:
                logger.warning("⚠️  No options symbols configured! Set OPTIONS_SYMBOLS environment variable.")
            logger.info("")
            
            # Initialize database
            if self.db:
                logger.info("💾 Initializing database connection...")
                if self.db.connect():
                    logger.info("✅ Database ready (for options tracking)")
                else:
                    logger.warning("⚠️  Database connection failed - options data will not be saved")
            else:
                logger.warning("⚠️  Database not configured - options data will not be saved")
            
            # Initialize notifications
            if self.notification_service:
                recipients = self.notification_service.get_alert_recipients(use_cache=False)
                if recipients:
                    logger.info(f"📧 Email notifications enabled - {len(recipients)} recipient(s)")
                else:
                    logger.info("📧 Email notifications configured but no recipients found in alert_recipients table")
            else:
                logger.info("📧 Email notifications not configured - GMAIL_USER and GMAIL_PASSWORD required")
            
            # Initialize order tracker
            if self.order_tracker:
                logger.info(f"📋 Large order tracking enabled (>= ${self.order_tracker.min_order_value:,.0f})")
                logger.info(f"   Tracks: Options contracts only")
            else:
                logger.warning("⚠️  Order tracker not available - large orders will not be tracked")
            
            # Initialize trade tracker
            if self.trade_tracker:
                logger.info(f"💰 Large trade tracking enabled (>= ${self.trade_tracker.min_trade_value:,.0f})")
            else:
                logger.warning("⚠️  Trade tracker not available - large trades will not be tracked")
            
            # Initialize unusual volume tracker
            if self.unusual_volume_tracker:
                threshold = self.unusual_volume_tracker.unusual_threshold
                logger.info(f"🚨 Unusual volume detection enabled (>= {threshold}x average volume)")
            else:
                logger.warning("⚠️  Unusual volume tracker not available - unusual volume will not be detected")
            
            logger.info("")
            
            # Initialize stream client
            self.stream_client = StreamClient(
                client=self.client,
                account_id=None,  # Not needed for market data
                enforce_enums=False,  # Allow integer field IDs instead of enum types
            )
            
            logger.info("🔌 Initializing stream client...")
            self.running = True
            
            # Register message handlers - OPTIONS ONLY
            self.stream_client.add_level_one_option_handler(self.process_quote)
            self.stream_client.add_options_book_handler(self.process_order_book)
            
            logger.info("✅ Message handlers registered (Options Level 1 + Order Book)")
            
            # Log scanning mode
            if self.scan_all_orders:
                logger.info("🔍 Mode: Scanning ALL orders from order book (every order will be saved)")
            else:
                logger.info("🔍 Mode: Scanning LARGE orders only (>= $50k)")
            
            # Login to stream
            logger.info("🔐 Connecting to Schwab streaming API...")
            try:
                await self.stream_client.login()
                logger.info("✅ Stream connected successfully")
                logger.info("")
            except Exception as login_error:
                error_str = str(login_error)
                if "refresh_token_authentication_error" in error_str or "refresh token" in error_str.lower():
                    logger.warning("")
                    logger.warning("⚠️  Refresh token expired - triggering OAuth to get new token...")
                    logger.warning("")
                    
                    # Delete expired token so OAuth can run
                    if self.token_path.exists():
                        backup_path = Path("token.json.expired")
                        if backup_path.exists():
                            backup_path.unlink()
                        self.token_path.rename(backup_path)
                        logger.info(f"📦 Backed up expired token to {backup_path}")
                    
                    # Check if we're in production
                    is_production = (
                        os.getenv("AWS_EXECUTION_ENV") or
                        os.getenv("ECS_CONTAINER_METADATA_URI") or
                        os.getenv("EC2_INSTANCE_ID") or
                        os.getenv("GOOGLE_CLOUD_PROJECT") or
                        os.getenv("GCE_INSTANCE") or
                        os.getenv("PRODUCTION") == "true"
                    )
                    
                    if is_production:
                        logger.error("")
                        logger.error("=" * 80)
                        logger.error("❌ REFRESH TOKEN EXPIRED - Cannot perform OAuth in production")
                        logger.error("=" * 80)
                        logger.error("")
                        logger.error("Your SCHWAB_TOKEN_JSON contains an expired refresh_token.")
                        logger.error("You need to refresh it locally, then update the env var:")
                        logger.error("")
                        logger.error("  1. Refresh token locally: python3 schwab_streamer.py")
                        logger.error("  2. Extract new token: python3 scripts/extract_token.py")
                        logger.error("  3. Update SCHWAB_TOKEN_JSON in your production environment")
                        logger.error("")
                        logger.error("=" * 80)
                        raise
                    
                    # Trigger OAuth flow
                    logger.info("")
                    logger.info("=" * 80)
                    logger.info("🔄 REFRESHING TOKEN VIA OAUTH")
                    logger.info("=" * 80)
                    logger.info("")
                    logger.info("Starting OAuth flow to refresh token...")
                    logger.info(f"Using callback URL: {self.callback_url}")
                    logger.info("")
                    logger.info("⚠️  You will need to:")
                    logger.info("   1. Press ENTER when prompted (to open browser)")
                    logger.info("   2. Complete OAuth in browser")
                    logger.info("   3. Accept security warning if shown")
                    logger.info("")
                    
                    from schwab.auth import easy_client
                    
                    try:
                        self.client = easy_client(
                            api_key=self.app_key,
                            app_secret=self.app_secret,
                            callback_url=self.callback_url,
                            token_path=str(self.token_path),
                            asyncio=False,
                            interactive=True,
                        )
                        logger.info("")
                        logger.info("✅ OAuth successful - token refreshed and saved!")
                        logger.info("")
                        
                        # Re-initialize stream client with new token
                        from schwab.streaming import StreamClient
                        self.stream_client = StreamClient(
                            client=self.client,
                            account_id=None,
                            enforce_enums=False,
                        )
                        self.stream_client.add_level_one_option_handler(self.process_quote)
                        self.stream_client.add_options_book_handler(self.process_order_book)
                        
                        # Try login again with new token
                        logger.info("🔐 Connecting to Schwab streaming API with new token...")
                        await self.stream_client.login()
                        logger.info("✅ Stream connected successfully")
                        logger.info("")
                        
                    except Exception as oauth_error:
                        logger.error(f"❌ OAuth failed: {oauth_error}")
                        raise
                else:
                    # Other streaming error
                    raise
            
            # Subscribe to OPTIONS only (no stocks)
            if len(self.symbols) == 0:
                logger.error("❌ No options symbols configured!")
                logger.error("   Set OPTIONS_SYMBOLS environment variable with comma-separated options symbols")
                logger.error("   Example: OPTIONS_SYMBOLS=AAPL_240119C150,NVDA_240119C400,TSLA_240119P200")
                return
            
            # Fields: 0=Symbol, 1=Bid, 2=Ask, 3=Last, 4=Bid Size, 5=Ask Size, 8=Total Volume
            logger.info(f"📡 Subscribing to {len(self.symbols)} OPTIONS contracts...")
            
            # Subscribe in batches (API may have limits)
            batch_size = 100
            for i in range(0, len(self.symbols), batch_size):
                batch = self.symbols[i:i+batch_size]
                
                # Subscribe to Options Level 1 quotes
                try:
                    await self.stream_client.level_one_options_subs(
                        symbols=batch,
                        fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
                    )
                    logger.info(f"   ✅ Subscribed Level 1 Options for batch {i//batch_size + 1} ({len(batch)} contracts)")
                except Exception as e:
                    logger.warning(f"   ⚠️  Level 1 Options subscription failed for batch {i//batch_size + 1}: {e}")
                
                # Subscribe to Options order book (Level 2)
                try:
                    await self.stream_client.options_book_subs(symbols=batch)
                    logger.info(f"   ✅ Subscribed Options Order Book for batch {i//batch_size + 1} ({len(batch)} contracts)")
                except Exception as e:
                    logger.warning(f"   ⚠️  Options order book subscription failed for batch {i//batch_size + 1}: {e}")
                
                if i + batch_size < len(self.symbols):
                    await asyncio.sleep(0.5)  # Small delay between batches
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Subscribed to all {len(self.symbols)} OPTIONS contracts")
            logger.info("   📊 Level 1: Top bid/ask quotes")
            logger.info("   📚 Order Book: ALL orders at each price level")
            logger.info("=" * 80)
            logger.info("📈 OPTIONS SCANNING ACTIVE - Detecting unusual volume in real-time")
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

