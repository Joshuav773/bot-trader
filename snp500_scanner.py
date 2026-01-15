#!/usr/bin/env python3
"""
S&P 500 Scanner - Real-time market data monitoring
Scans all S&P 500 stocks during NY session and stores data for analysis
"""
import sys
import os
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from schwab_streamer import SchwabStreamer

# S&P 500 symbols (top 100 for testing - add full list as needed)
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
    # Add more symbols to reach 500...
]


class SP500Scanner:
    """S&P 500 real-time scanner"""
    
    def __init__(self, db_config=None):
        self.streamer = SchwabStreamer()
        self.db_config = db_config
        self.running = False
        self.data_buffer = []
        self.symbols = SP500_SYMBOLS
        
    def is_market_hours(self):
        """Check if current time is within NY session (9:30 AM - 4:00 PM ET)"""
        now = datetime.now(timezone.utc)
        # Convert to ET (UTC-5 or UTC-4 depending on DST)
        et_offset = -5 if now.month < 3 or now.month > 11 or (now.month == 3 and now.day < 8) or (now.month == 11 and now.day > 1) else -4
        et_time = now.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=et_offset)))
        
        # NY session: 9:30 AM - 4:00 PM ET
        market_open = et_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = et_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= et_time <= market_close
    
    def store_data(self, data):
        """Store market data in database (implement based on your DB)"""
        if not self.db_config:
            # For now, just buffer in memory
            self.data_buffer.append(data)
            if len(self.data_buffer) > 1000:
                # In production, flush to DB
                print(f"📊 Buffer size: {len(self.data_buffer)} entries")
                self.data_buffer = []  # Clear buffer
            return
        
        # TODO: Implement database storage
        # Example: Save to PostgreSQL, MongoDB, etc.
        pass
    
    def process_quote(self, msg):
        """Process incoming quote data"""
        try:
            # Parse message structure
            if isinstance(msg, dict):
                service = msg.get('service', '')
                if service == 'LEVELONE_EQUITIES':
                    content = msg.get('content', [])
                    for item in content:
                        if isinstance(item, dict):
                            symbol = item.get('key', item.get('1', ''))
                            
                            # Extract quote data
                            quote_data = {
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'symbol': symbol,
                                'bid': item.get('2', None),  # Bid price
                                'ask': item.get('3', None),  # Ask price
                                'last': item.get('4', None),  # Last price
                                'bid_size': item.get('5', None),
                                'ask_size': item.get('6', None),
                                'volume': item.get('8', None),  # Total volume
                            }
                            
                            # Store data
                            self.store_data(quote_data)
                            
                            # Log (can be removed in production)
                            if symbol in ['SPY', 'AAPL', 'MSFT']:  # Log a few symbols
                                print(f"📊 {symbol}: ${quote_data.get('last', 'N/A')} | "
                                      f"Bid: ${quote_data.get('bid', 'N/A')} | "
                                      f"Ask: ${quote_data.get('ask', 'N/A')} | "
                                      f"Vol: {quote_data.get('volume', 'N/A')}")
        except Exception as e:
            print(f"⚠️  Error processing quote: {e}")
    
    async def scan_async(self):
        """Start scanning S&P 500 stocks"""
        print("=" * 80)
        print("📊 S&P 500 SCANNER")
        print("=" * 80)
        print(f"\n📋 Configuration:")
        print(f"   Symbols: {len(self.symbols)} stocks")
        print(f"   Mode: Real-time Level 1 quotes")
        print(f"   Session: NY market hours (9:30 AM - 4:00 PM ET)")
        print(f"\n⏳ Authenticating...")
        
        # Authenticate
        if not self.streamer.authenticate():
            print("❌ Authentication failed!")
            return False
        
        print("✅ Authenticated")
        
        # Check market hours
        if not self.is_market_hours():
            print("\n⚠️  Outside market hours (NY session: 9:30 AM - 4:00 PM ET)")
            print("   Scanner will still run, but no live data will be available")
        
        try:
            from schwab.streaming import StreamClient
            
            print("\n📡 Connecting to stream...")
            
            # Initialize stream client
            stream_client = StreamClient(
                client=self.streamer.client,
                account_id=None,
            )
            
            # Register message handler
            stream_client.add_level_one_equity_handler(self.process_quote)
            
            # Login to stream
            await stream_client.login()
            print("✅ Stream connected")
            
            # Subscribe to S&P 500 symbols (in batches if needed - API may have limits)
            print(f"\n📊 Subscribing to {len(self.symbols)} symbols...")
            
            # Schwab API may have symbol limits per subscription
            # Subscribe in batches if needed
            batch_size = 100  # Adjust based on API limits
            for i in range(0, len(self.symbols), batch_size):
                batch = self.symbols[i:i+batch_size]
                await stream_client.level_one_equity_subs(
                    symbols=batch,
                    fields=[0, 1, 2, 3, 4, 5, 6, 8]  # Symbol, Bid, Ask, Last, Bid Size, Ask Size, Volume
                )
                print(f"   ✅ Subscribed to batch {i//batch_size + 1} ({len(batch)} symbols)")
                if i + batch_size < len(self.symbols):
                    await asyncio.sleep(0.5)  # Small delay between batches
            
            print(f"\n✅ Subscribed to all {len(self.symbols)} symbols")
            print("\n" + "=" * 80)
            print("📈 SCANNING S&P 500 (Press Ctrl+C to stop)")
            print("=" * 80)
            print("\nData is being collected and stored...\n")
            
            # Handle messages
            self.running = True
            message_count = 0
            try:
                while self.running:
                    await stream_client.handle_message()
                    message_count += 1
                    if message_count % 1000 == 0:
                        print(f"📊 Processed {message_count} messages | Buffer: {len(self.data_buffer)} entries")
            except KeyboardInterrupt:
                print("\n\n🛑 Interrupted by user")
            
            # Logout
            print("\n📴 Disconnecting...")
            await stream_client.logout()
            print("✅ Disconnected")
            
            print(f"\n📊 Summary:")
            print(f"   Messages processed: {message_count}")
            print(f"   Data entries collected: {len(self.data_buffer)}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def scan(self):
        """Start scanning (sync wrapper)"""
        try:
            asyncio.run(self.scan_async())
        except KeyboardInterrupt:
            self.running = False
            print("\n✅ Scanner stopped")
    
    def stop(self):
        """Stop scanning"""
        self.running = False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="S&P 500 Real-time Scanner")
    parser.add_argument(
        "--symbols-file",
        help="File containing S&P 500 symbols (one per line)"
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=100,
        help="Maximum number of symbols to scan (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Load symbols if file provided
    symbols = SP500_SYMBOLS
    if args.symbols_file:
        try:
            with open(args.symbols_file, 'r') as f:
                symbols = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"⚠️  Error loading symbols file: {e}")
            print("   Using default symbols")
    
    # Limit symbols if specified
    if args.max_symbols:
        symbols = symbols[:args.max_symbols]
    
    scanner = SP500Scanner()
    scanner.symbols = symbols
    
    print(f"\n🚀 Starting S&P 500 Scanner with {len(symbols)} symbols...\n")
    scanner.scan()


if __name__ == "__main__":
    main()


