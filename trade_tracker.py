"""
Large Trade Tracker
Tracks trades >= $200k and records entry/exit prices
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class LargeTradeTracker:
    """Track large trades ($200k+) with entry/exit prices"""
    
    def __init__(self, min_trade_value: float = 200000.0):
        self.min_trade_value = min_trade_value  # $200k minimum
        self.previous_volumes = {}  # Track previous volume per symbol
        self.active_trades = {}  # Track active large trades
        self.trades_tracked = 0
        
        # For tracking entry/exit points
        self.trade_state = defaultdict(lambda: {
            'volume_start': None,
            'price_start': None,
            'volume_accumulated': 0,
            'trade_value_accumulated': 0.0,
            'start_time': None,
            'last_update': None
        })
    
    def process_quote(self, quote_data: Dict) -> Optional[Dict]:
        """
        Process quote and detect large trades
        
        Returns trade data if large trade detected, None otherwise
        """
        try:
            symbol = quote_data.get('symbol')
            last_price = quote_data.get('last')
            volume = quote_data.get('volume')
            timestamp = quote_data.get('timestamp')
            
            if not symbol or not last_price or not volume:
                return None
            
            # Parse timestamp
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    dt = datetime.now(timezone.utc)
            else:
                dt = timestamp if isinstance(timestamp, datetime) else datetime.now(timezone.utc)
            
            # Get previous volume
            prev_volume = self.previous_volumes.get(symbol, 0)
            
            # Calculate volume delta
            volume_delta = volume - prev_volume
            
            # Only process if volume increased (trade happened)
            if volume_delta <= 0:
                # Update previous volume but don't track
                self.previous_volumes[symbol] = volume
                return None
            
            # Update previous volume
            self.previous_volumes[symbol] = volume
            
            # Get trade state for this symbol
            state = self.trade_state[symbol]
            
            # Initialize trade tracking if this is a new trade sequence
            if state['volume_start'] is None:
                state['volume_start'] = prev_volume
                state['price_start'] = last_price
                state['volume_accumulated'] = 0
                state['trade_value_accumulated'] = 0.0
                state['start_time'] = dt
                state['last_update'] = dt
            
            # Accumulate trade volume and value
            state['volume_accumulated'] += volume_delta
            trade_value_increment = volume_delta * float(last_price)
            state['trade_value_accumulated'] += trade_value_increment
            state['last_update'] = dt
            
            # Check if accumulated trade value meets threshold
            if state['trade_value_accumulated'] >= self.min_trade_value:
                # Large trade detected!
                entry_price = state['price_start']
                exit_price = last_price
                total_volume = state['volume_accumulated']
                total_value = state['trade_value_accumulated']
                start_time = state['start_time']
                end_time = dt
                
                # Create trade record
                trade_record = {
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'entry_time': start_time,
                    'exit_time': end_time,
                    'volume': total_volume,
                    'trade_value_usd': total_value,
                    'price_change': float(exit_price) - float(entry_price) if entry_price and exit_price else 0,
                    'price_change_pct': ((float(exit_price) - float(entry_price)) / float(entry_price) * 100) if entry_price and exit_price and float(entry_price) > 0 else 0
                }
                
                # Reset trade state for next tracking period
                state['volume_start'] = None
                state['price_start'] = None
                state['volume_accumulated'] = 0
                state['trade_value_accumulated'] = 0.0
                state['start_time'] = None
                state['last_update'] = None
                
                self.trades_tracked += 1
                
                logger.info(
                    f"💰 Large trade detected: {symbol} | "
                    f"Value: ${total_value:,.2f} | "
                    f"Entry: ${entry_price} → Exit: ${exit_price} | "
                    f"Vol: {total_volume:,}"
                )
                
                return trade_record
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing quote for trade tracking: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get tracking statistics"""
        return {
            'trades_tracked': self.trades_tracked,
            'min_trade_value': self.min_trade_value,
            'symbols_tracked': len(self.previous_volumes),
            'active_trades': len([s for s in self.trade_state.values() if s['volume_start'] is not None])
        }

