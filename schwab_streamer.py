"""
Schwab Streaming Client
Connects to Schwab Streaming API and processes market data.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure logging
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


class SchwabStreamer:
    """Schwab streaming client"""
    
    def __init__(self):
        self.app_key = SCHWAB_APP_KEY
        self.app_secret = SCHWAB_APP_SECRET
        self.callback_url = SCHWAB_CALLBACK_URL
        self.token_path = TOKEN_PATH
        self.client = None
        self.stream_client = None
        self.running = False
        
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
    
    async def start_streaming_async(self):
        """Start streaming market data (async version)"""
        if not self.client:
            logger.error("Not authenticated. Call authenticate() first.")
            return
        
        try:
            from schwab.streaming import StreamClient
            
            # Initialize stream client
            self.stream_client = StreamClient(
                client=self.client,
                account_id=None,  # Not needed for market data
            )
            
            logger.info("Starting Schwab stream...")
            self.running = True
            
            # Subscribe to market data (example: SPY, QQQ, AAPL)
            symbols = ["SPY", "QQQ", "AAPL"]
            
            def on_message(msg):
                """Handle incoming stream messages"""
                logger.info(f"📊 Message received: {msg}")
                # Process the message here
            
            # Register message handler
            self.stream_client.add_level_one_equity_handler(on_message)
            
            # Login to stream
            await self.stream_client.login()
            logger.info("✅ Stream connected")
            
            # Subscribe to symbols with fields
            # Fields: 0=Symbol, 1=Bid, 2=Ask, 3=Last, 4=Bid Size, 8=Total Volume
            await self.stream_client.level_one_equity_subs(
                symbols=symbols,
                fields=[0, 1, 2, 3, 4, 8]  # Standard equity fields
            )
            
            logger.info(f"✅ Subscribed to {len(symbols)} symbols: {', '.join(symbols)}")
            logger.info("Stream is active - messages will be logged as they arrive")
            
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
        import asyncio
        try:
            asyncio.run(self.start_streaming_async())
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
            self.running = False
    
    async def stop_async(self):
        """Stop streaming (async)"""
        logger.info("Stopping stream...")
        self.running = False
        if self.stream_client:
            try:
                await self.stream_client.logout()
                logger.info("✅ Stream disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting stream: {e}")
    
    def stop(self):
        """Stop streaming (sync wrapper)"""
        import asyncio
        if self.stream_client:
            try:
                asyncio.run(self.stop_async())
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
                self.running = False


def main():
    """Main entry point"""
    logger.info("🚀 Starting Schwab Streamer...")
    
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
        logger.info("\n🛑 Stopping streamer...")
        streamer.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

