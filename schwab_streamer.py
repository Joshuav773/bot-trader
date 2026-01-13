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
        self.trade_tracker = LargeTradeTracker(min_trade_value=200000.0) if TRADE_TRACKER_AVAILABLE else None
        self.notifications_sent = 0
        self.large_trades_saved = 0
        
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
                            
                            # Track large trades only (>= $200k)
                            if self.trade_tracker:
                                large_trade = self.trade_tracker.process_quote(quote_data)
                                if large_trade:
                                    # Save large trade to database
                                    if self.db and self.db.save_large_trade(large_trade):
                                        self.large_trades_saved += 1
                                        logger.info(
                                            f"💰 Large trade detected: {symbol} | "
                                            f"Value: ${large_trade.get('trade_value_usd', 0):,.2f} | "
                                            f"Entry: ${large_trade.get('entry_price')} → Exit: ${large_trade.get('exit_price')} | "
                                            f"Vol: {large_trade.get('volume', 0):,}"
                                        )
                                        
                                        # Send email notification for large trades only
                                        if self.notification_service:
                                            sent = self.notification_service.send_quote_notification(quote_data)
                                            if sent > 0:
                                                self.notifications_sent += sent
                            
                            # Log status every 100 messages (minimal logging)
                            if self.message_count % 100 == 0:
                                status_msg = (
                                    f"📈 Status: {self.message_count} messages processed | "
                                    f"Large trades detected: {self.large_trades_saved} | "
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
            logger.info(f"   Mode: Real-time Level 1 quotes")
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
            
            # Register message handler
            self.stream_client.add_level_one_equity_handler(self.process_quote)
            logger.info("✅ Message handler registered")
            
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
                await self.stream_client.level_one_equity_subs(
                    symbols=batch,
                    fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
                )
                logger.info(f"   ✅ Subscribed to batch {i//batch_size + 1} ({len(batch)} symbols)")
                if i + batch_size < len(self.symbols):
                    await asyncio.sleep(0.5)  # Small delay between batches
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Subscribed to all {len(self.symbols)} symbols")
            logger.info("=" * 80)
            logger.info("📈 STREAMING ACTIVE - Real-time quotes are being collected")
            logger.info("   Press Ctrl+C to stop")
            logger.info("")
            
            # Handle messages in a loop
            while self.running:
                await self.stream_client.handle_message()
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            self.running = False
            if self.stream_client:
                try:
                    await self.stream_client.logout()
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

