"""
Database connection and operations for streaming data
"""
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values, RealDictCursor
    from psycopg2.pool import SimpleConnectionPool
except ImportError:
    logger.warning("psycopg2 not installed. Run: pip install psycopg2-binary")
    psycopg2 = None


class Database:
    """Database connection and operations"""
    
    def __init__(self):
        self.db_url = (
            os.getenv("DATABASE_URL") or 
            os.getenv("NEON_DATABASE_URL") or 
            os.getenv("POSTGRES_URL")
        )
        self.conn = None
        self.pool = None
        
        if not self.db_url:
            logger.warning("DATABASE_URL not found. Database operations will be disabled.")
    
    def connect(self):
        """Connect to database"""
        if not self.db_url:
            return False
        
        if not psycopg2:
            logger.error("psycopg2 not installed")
            return False
        
        try:
            self.conn = psycopg2.connect(self.db_url)
            logger.info("✅ Connected to database")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def save_quote_to_price_snapshots(self, quote_data: Dict) -> bool:
        """
        Save quote data to price_snapshots table
        
        Note: price_snapshots requires order_flow_id, so we'll need to handle this
        For now, we'll create a placeholder approach or extend the table
        """
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            cursor = self.conn.cursor()
            
            # price_snapshots schema:
            # id, order_flow_id (required), ticker, snapshot_time, interval_minutes, price, price_change_pct
            
            # For streaming data, we don't have order_flow_id
            # Option 1: Create a new table for streaming quotes (recommended)
            # Option 2: Make order_flow_id nullable (requires migration)
            # Option 3: Use a placeholder order_flow_id
            
            # For now, let's check if we should use a different approach
            # Let's save to a new table or extend existing
            
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error saving quote: {e}")
            return False
    
    def save_quotes_batch(self, quotes: List[Dict]) -> int:
        """Save multiple quotes in a batch (more efficient)"""
        if not quotes:
            return 0
        
        if not self.conn:
            if not self.connect():
                return 0
        
        saved = 0
        try:
            cursor = self.conn.cursor()
            
            # Since price_snapshots requires order_flow_id, we have options:
            # 1. Create streaming_quotes table (recommended)
            # 2. Extend price_snapshots
            
            # For now, let's create a streaming_quotes table approach
            # But first, let's check what the user wants to do
            
            cursor.close()
            self.conn.commit()
            return saved
        except Exception as e:
            logger.error(f"Error saving quotes batch: {e}")
            if self.conn:
                self.conn.rollback()
            return saved
    
    def create_streaming_quotes_table(self) -> bool:
        """Create a new table for streaming quotes"""
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS streaming_quotes (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    bid NUMERIC(12, 4),
                    ask NUMERIC(12, 4),
                    last_price NUMERIC(12, 4),
                    bid_size INTEGER,
                    ask_size INTEGER,
                    volume BIGINT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_streaming_quotes_symbol ON streaming_quotes(symbol);
                CREATE INDEX IF NOT EXISTS idx_streaming_quotes_timestamp ON streaming_quotes(timestamp);
                CREATE INDEX IF NOT EXISTS idx_streaming_quotes_symbol_timestamp ON streaming_quotes(symbol, timestamp);
            """)
            
            self.conn.commit()
            cursor.close()
            logger.info("✅ Created streaming_quotes table")
            return True
        except Exception as e:
            logger.error(f"Error creating streaming_quotes table: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def save_single_quote(self, quote: Dict) -> bool:
        """Save a single streaming quote immediately"""
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            cursor = self.conn.cursor()
            
            # Parse timestamp
            timestamp = quote.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Insert single quote
            cursor.execute("""
                INSERT INTO streaming_quotes 
                (symbol, timestamp, bid, ask, last_price, bid_size, ask_size, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                quote.get('symbol'),
                timestamp,
                quote.get('bid'),
                quote.get('ask'),
                quote.get('last'),
                quote.get('bid_size'),
                quote.get('ask_size'),
                quote.get('volume'),
            ))
            
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error saving single quote: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def save_streaming_quotes(self, quotes: List[Dict]) -> int:
        """Save multiple streaming quotes in a batch (more efficient)"""
        if not quotes:
            return 0
        
        if not self.conn:
            if not self.connect():
                return 0
        
        try:
            cursor = self.conn.cursor()
            
            # Prepare data for bulk insert
            values = []
            for quote in quotes:
                timestamp = quote.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                values.append((
                    quote.get('symbol'),
                    timestamp,
                    quote.get('bid'),
                    quote.get('ask'),
                    quote.get('last'),
                    quote.get('bid_size'),
                    quote.get('ask_size'),
                    quote.get('volume'),
                ))
            
            # Bulk insert
            execute_values(
                cursor,
                """
                INSERT INTO streaming_quotes 
                (symbol, timestamp, bid, ask, last_price, bid_size, ask_size, volume)
                VALUES %s
                """,
                values
            )
            
            self.conn.commit()
            saved = len(values)
            cursor.close()
            
            logger.debug(f"💾 Saved {saved} quotes to database (batch)")
            return saved
        except Exception as e:
            logger.error(f"Error saving streaming quotes: {e}")
            if self.conn:
                self.conn.rollback()
            return 0
    
    def save_large_trade(self, trade: Dict) -> bool:
        """Save large trade to order_flow table"""
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            cursor = self.conn.cursor()
            
            # Parse timestamps
            entry_time = trade.get('entry_time')
            exit_time = trade.get('exit_time')
            
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            if isinstance(exit_time, str):
                exit_time = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            
            # Save to order_flow table
            # Using entry_time as timestamp, storing entry/exit info in raw_data
            cursor.execute("""
                INSERT INTO order_flow 
                (ticker, order_type, order_size_usd, price, timestamp, source, raw_data, display_ticker, instrument, order_side)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trade.get('symbol'),
                'large_trade',  # order_type
                trade.get('trade_value_usd'),
                trade.get('entry_price'),  # Use entry price as primary price
                entry_time,  # timestamp (entry time)
                'streamer',  # source
                f"entry_price={trade.get('entry_price')},exit_price={trade.get('exit_price')},entry_time={entry_time.isoformat()},exit_time={exit_time.isoformat()},volume={trade.get('volume')},price_change={trade.get('price_change')},price_change_pct={trade.get('price_change_pct')}",
                trade.get('symbol'),  # display_ticker
                'equity',  # instrument
                None  # order_side
            ))
            
            self.conn.commit()
            cursor.close()
            
            logger.debug(f"💾 Saved large trade to order_flow: {trade.get('symbol')} ${trade.get('trade_value_usd'):,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving large trade: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def save_large_order(self, order: Dict) -> bool:
        """Save large order to order_flow table"""
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            cursor = self.conn.cursor()
            
            # Parse timestamp
            timestamp = order.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now(timezone.utc)
            
            # Prepare raw_data JSON string
            import json
            raw_data = json.dumps({
                'order_type': order.get('order_type'),
                'order_size_shares': order.get('order_size_shares'),
                'bid_size': order.get('bid_size'),
                'ask_size': order.get('ask_size'),
                'spread': order.get('spread'),
                'instrument': order.get('instrument'),
            })
            
            # Save to order_flow table
            cursor.execute("""
                INSERT INTO order_flow 
                (ticker, order_type, order_size_usd, price, timestamp, source, raw_data, display_ticker, instrument, order_side)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order.get('symbol'),
                f"large_order_{order.get('order_type', 'UNKNOWN').lower()}",  # order_type
                order.get('order_value_usd'),
                order.get('price'),
                timestamp,
                'streamer',  # source
                raw_data,
                order.get('symbol'),  # display_ticker
                order.get('instrument', 'equity'),  # instrument (equity or option)
                order.get('order_type'),  # order_side (BUY or SELL)
            ))
            
            self.conn.commit()
            cursor.close()
            
            logger.debug(f"💾 Saved large order to order_flow: {order.get('symbol')} {order.get('order_type')} ${order.get('order_value_usd'):,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving large order: {e}", exc_info=True)
            if self.conn:
                self.conn.rollback()
            return False
    
    def save_all_order(self, order: Dict) -> bool:
        """Save ANY order (regardless of size) to order_flow table"""
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            cursor = self.conn.cursor()
            
            # Parse timestamp
            timestamp = order.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now(timezone.utc)
            
            # Prepare raw_data JSON string
            import json
            raw_data = json.dumps({
                'order_type': order.get('order_type'),
                'order_size_shares': order.get('order_size_shares'),
                'detection_method': order.get('detection_method'),
                'exchange': order.get('exchange'),
                'book_time': order.get('book_time'),
                'price_level': order.get('price_level'),
                'instrument': order.get('instrument'),
            })
            
            # Save to order_flow table
            cursor.execute("""
                INSERT INTO order_flow 
                (ticker, order_type, order_size_usd, price, timestamp, source, raw_data, display_ticker, instrument, order_side)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order.get('symbol'),
                order.get('order_type', 'ORDER').lower(),  # order_type
                order.get('order_value_usd', 0),
                order.get('price'),
                timestamp,
                'order_book',  # source
                raw_data,
                order.get('symbol'),  # display_ticker
                order.get('instrument', 'equity'),  # instrument
                order.get('order_side', order.get('order_type', 'UNKNOWN')),  # order_side
            ))
            
            self.conn.commit()
            cursor.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving order: {e}", exc_info=True)
            if self.conn:
                self.conn.rollback()
            return False


# Global database instance
_db = None

def get_db() -> Database:
    """Get database instance (singleton)"""
    global _db
    if _db is None:
        _db = Database()
    return _db

