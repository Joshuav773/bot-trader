#!/usr/bin/env python3
"""
Test Script for Schwab Streamer
Shows real-time market data streaming with formatted output
"""
import sys
import os
import signal
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schwab_streamer import SchwabStreamer


class StreamTester:
    """Test class for streaming with better output formatting"""
    
    def __init__(self):
        self.streamer = SchwabStreamer()
        self.message_count = 0
        self.running = True
        
    def format_message(self, msg):
        """Format stream message for display"""
        try:
            # Stream messages have different formats
            # Level 1 equity messages contain service='LEVELONE_EQUITIES' and data
            if isinstance(msg, dict):
                service = msg.get('service', '')
                if service == 'LEVELONE_EQUITIES':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('1', 'UNKNOWN'))  # Field 1 is symbol
                            bid = item.get('2', 'N/A')  # Field 2 is bid
                            ask = item.get('3', 'N/A')  # Field 3 is ask
                            last = item.get('4', 'N/A')  # Field 4 is last
                            bid_size = item.get('5', 'N/A')  # Field 5 is bid size
                            volume = item.get('8', 'N/A')  # Field 8 is total volume
                            
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            return f"[{timestamp}] {symbol:6} | Bid: ${bid:>8} | Ask: ${ask:>8} | Last: ${last:>8} | Vol: {volume}"
            
            # If we can't parse it, return the raw message (truncated)
            msg_str = str(msg)[:200]
            return f"📊 Raw: {msg_str}"
            
        except Exception as e:
            return f"⚠️  Format error: {e} | Raw: {str(msg)[:100]}"
    
    def on_message(self, msg):
        """Handle incoming stream messages"""
        self.message_count += 1
        formatted = self.format_message(msg)
        print(formatted)
        
        # Print raw message every 10th message for debugging
        if self.message_count % 10 == 0:
            print(f"   (Message #{self.message_count} | Raw: {str(msg)[:150]}...)")
    
    async def test_streaming(self, symbols=None, max_messages=50, timeout=60):
        """Test streaming with specified symbols"""
        if not symbols:
            symbols = ["SPY", "QQQ", "AAPL"]
        
        print("=" * 80)
        print("🧪 SCHWAB STREAMER TEST")
        print("=" * 80)
        print(f"\n📋 Configuration:")
        print(f"   Symbols: {', '.join(symbols)}")
        print(f"   Max messages: {max_messages} (0 = unlimited)")
        print(f"   Timeout: {timeout} seconds")
        print(f"\n⏳ Authenticating...")
        
        # Authenticate
        if not self.streamer.authenticate():
            print("❌ Authentication failed!")
            return False
        
        print("✅ Authenticated successfully")
        
        try:
            from schwab.streaming import StreamClient
            
            print("\n📡 Connecting to stream...")
            
            # Initialize stream client
            stream_client = StreamClient(
                client=self.streamer.client,
                account_id=None,
            )
            
            # Register message handler
            stream_client.add_level_one_equity_handler(self.on_message)
            
            # Login to stream
            await stream_client.login()
            print("✅ Stream connected")
            
            # Subscribe to symbols
            print(f"\n📊 Subscribing to symbols: {', '.join(symbols)}...")
            await stream_client.level_one_equity_subs(
                symbols=symbols,
                fields=[0, 1, 2, 3, 4, 8]  # Symbol, Bid, Ask, Last, Bid Size, Volume
            )
            
            print("✅ Subscribed successfully")
            print("\n" + "=" * 80)
            print("📈 STREAMING LIVE DATA (Press Ctrl+C to stop)")
            print("=" * 80)
            print("\nFormat: [Time] Symbol | Bid | Ask | Last | Volume\n")
            
            # Handle messages with timeout
            start_time = asyncio.get_event_loop().time()
            try:
                while self.running and self.message_count < max_messages:
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if timeout > 0 and elapsed > timeout:
                        print(f"\n⏱️  Timeout reached ({timeout}s)")
                        break
                    
                    # Handle message (with timeout)
                    try:
                        await asyncio.wait_for(stream_client.handle_message(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # No message received, continue
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        if self.running:
                            print(f"⚠️  Error handling message: {e}")
                        break
                
            except KeyboardInterrupt:
                print("\n\n🛑 Interrupted by user")
            
            # Logout
            print("\n📴 Disconnecting...")
            await stream_client.logout()
            print("✅ Disconnected")
            
            print(f"\n📊 Summary: Received {self.message_count} messages")
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop(self):
        """Stop streaming"""
        self.running = False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Schwab streaming")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["SPY", "QQQ", "AAPL"],
        help="Symbols to stream (default: SPY QQQ AAPL)"
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=50,
        help="Maximum number of messages to receive (default: 50, 0 = unlimited)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds (default: 60, 0 = no timeout)"
    )
    
    args = parser.parse_args()
    
    tester = StreamTester()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n🛑 Stopping...")
        tester.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run test
    try:
        success = asyncio.run(tester.test_streaming(
            symbols=args.symbols,
            max_messages=args.max_messages,
            timeout=args.timeout
        ))
        
        if success:
            print("\n✅ Test completed successfully!")
            return 0
        else:
            print("\n❌ Test failed!")
            return 1
            
    except KeyboardInterrupt:
        tester.stop()
        print("\n✅ Test stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

