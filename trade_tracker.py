"""
Enhanced Large Trade Tracker
Tracks large executed trades >= $50k with improved detection
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LargeTradeTracker:
    """Enhanced trade tracker with better volume spike detection"""
    
    def __init__(self, min_trade_value: float = 50000.0):
        self.min_trade_value = min_trade_value  # $50k minimum
        self.previous_volumes = {}  # Track previous volume per symbol
        self.previous_prices = {}  # Track previous prices
        self.active_trades = {}  # Track active large trades
        self.trades_tracked = 0
        
        # Deduplication
        self.recent_trades = defaultdict(lambda: deque(maxlen=5))  # Last 5 trades per symbol
        self.deduplication_window_seconds = 3
        
        # Volume spike detection (track recent volumes for better detection)
        self.recent_volumes = defaultdict(lambda: deque(maxlen=5))  # Last 5 volumes
        
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
            
            # Track recent volumes for spike detection
            self.recent_volumes[symbol].append(volume)
            
            # Calculate average recent volume (for spike detection)
            recent_volumes_list = list(self.recent_volumes[symbol])
            if len(recent_volumes_list) > 1:
                avg_recent_volume = sum(recent_volumes_list[:-1]) / (len(recent_volumes_list) - 1)
            else:
                avg_recent_volume = volume
            
            # Detect volume spike (volume significantly higher than average)
            volume_spike = False
            if avg_recent_volume > 0:
                volume_increase_pct = (volume_delta / avg_recent_volume) * 100 if avg_recent_volume > 0 else 0
                volume_spike = volume_increase_pct > 50  # 50% increase = spike
            
            # Only process if volume increased (trade happened)
            if volume_delta <= 0:
                # Update previous volume but don't track
                self.previous_volumes[symbol] = volume
                self.previous_prices[symbol] = float(last_price)
                return None
            
            # Get previous price for price change calculation
            prev_price = self.previous_prices.get(symbol, float(last_price))
            price_change = float(last_price) - prev_price
            price_change_pct = (price_change / prev_price * 100) if prev_price > 0 else 0
            
            # Update previous values
            self.previous_volumes[symbol] = volume
            self.previous_prices[symbol] = float(last_price)
            
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
            
            # Enhanced detection: Check if accumulated trade value meets threshold
            # Also check for immediate large volume spike (single large trade)
            immediate_large_trade = False
            if volume_delta * float(last_price) >= self.min_trade_value:
                # Single large trade detected (not accumulated)
                immediate_large_trade = True
            
            if state['trade_value_accumulated'] >= self.min_trade_value or immediate_large_trade:
                # Large trade detected!
                if immediate_large_trade and volume_delta * float(last_price) > state['trade_value_accumulated']:
                    # Single large trade is bigger than accumulated - use it
                    entry_price = prev_price
                    exit_price = last_price
                    total_volume = volume_delta
                    total_value = volume_delta * float(last_price)
                    start_time = dt  # Use current time for single trade
                    end_time = dt
                else:
                    # Use accumulated trade data
                    entry_price = state['price_start']
                    exit_price = last_price
                    total_volume = state['volume_accumulated']
                    total_value = state['trade_value_accumulated']
                    start_time = state['start_time']
                    end_time = dt
                
                # Deduplication check
                if self._is_duplicate_trade(symbol, total_value, exit_price, dt):
                    return None
                
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
                    'price_change_pct': ((float(exit_price) - float(entry_price)) / float(entry_price) * 100) if entry_price and exit_price and float(entry_price) > 0 else 0,
                    'volume_spike': volume_spike,
                    'detection_method': 'IMMEDIATE_SPIKE' if immediate_large_trade else 'ACCUMULATED'
                }
                
                # Reset trade state for next tracking period
                state['volume_start'] = None
                state['price_start'] = None
                state['volume_accumulated'] = 0
                state['trade_value_accumulated'] = 0.0
                state['start_time'] = None
                state['last_update'] = None
                
                self.trades_tracked += 1
                
                return trade_record
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing quote for trade tracking: {e}")
            return None
    
    def _is_duplicate_trade(self, symbol: str, value: float, price: float, timestamp: datetime) -> bool:
        """Check if this trade was recently detected (deduplication)"""
        recent = self.recent_trades[symbol]
        
        for prev_trade in recent:
            time_diff = (timestamp - prev_trade['timestamp']).total_seconds()
            if time_diff < self.deduplication_window_seconds:
                # Similar value and price = likely duplicate
                if (abs(prev_trade['value'] - value) < value * 0.15 and  # Within 15% value
                    abs(prev_trade['price'] - price) < price * 0.01):  # Within 1% price
                    return True
        
        # Not duplicate - add to recent trades
        recent.append({
            'value': value,
            'price': price,
            'timestamp': timestamp
        })
        return False
    
    def get_stats(self) -> Dict:
        """Get tracking statistics"""
        return {
            'trades_tracked': self.trades_tracked,
            'min_trade_value': self.min_trade_value,
            'symbols_tracked': len(self.previous_volumes),
            'active_trades': len([s for s in self.trade_state.values() if s['volume_start'] is not None])
        }

