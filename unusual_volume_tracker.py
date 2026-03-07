"""
Unusual Volume Tracker for Options
Tracks baseline volume and detects unusual activity
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class UnusualVolumeTracker:
    """Track unusual volume in options contracts"""
    
    def __init__(self, unusual_threshold: float = 2.0):
        """
        Initialize unusual volume tracker
        
        Args:
            unusual_threshold: Volume must be X times average to be "unusual" (default: 2.0 = 2x average)
        """
        self.unusual_threshold = unusual_threshold
        
        # Track volume history per symbol (20-day rolling window)
        self.volume_history = defaultdict(lambda: deque(maxlen=20))
        
        # Track baseline averages
        self.baseline_volumes = {}  # symbol -> average volume
        
        # Track unusual volume events
        self.unusual_events = []
        
        # Statistics
        self.unusual_detections = 0
    
    def get_average_volume(self, symbol: str) -> float:
        """Get average volume for symbol (baseline)"""
        if symbol in self.baseline_volumes:
            return self.baseline_volumes[symbol]
        
        # Calculate from history if available
        history = list(self.volume_history[symbol])
        if len(history) >= 5:  # Need at least 5 data points
            avg = sum(history) / len(history)
            self.baseline_volumes[symbol] = avg
            return avg
        
        return 0.0
    
    def is_unusual_volume(self, symbol: str, current_volume: int) -> bool:
        """
        Check if current volume is unusual compared to baseline
        
        Returns True if volume is >= threshold * average volume
        """
        if current_volume <= 0:
            return False
        
        avg_volume = self.get_average_volume(symbol)
        if avg_volume <= 0:
            # No baseline yet - not unusual
            return False
        
        ratio = current_volume / avg_volume
        return ratio >= self.unusual_threshold
    
    def process_quote(self, quote_data: Dict) -> Optional[Dict]:
        """
        Process quote and detect unusual volume
        
        Returns unusual volume event if detected, None otherwise
        Includes full quote details: bid, ask, last, volume, open interest
        """
        symbol = quote_data.get('symbol')
        volume = quote_data.get('volume')
        timestamp = quote_data.get('timestamp')
        
        if not symbol or not volume:
            return None
        
        try:
            volume_int = int(volume) if volume is not None else 0
            if volume_int <= 0:
                return None
            
            # Add to history
            self.volume_history[symbol].append(volume_int)
            
            # Update baseline (recalculate average)
            history = list(self.volume_history[symbol])
            if len(history) >= 5:
                avg = sum(history) / len(history)
                self.baseline_volumes[symbol] = avg
            
            # Check if unusual
            if self.is_unusual_volume(symbol, volume_int):
                avg_volume = self.get_average_volume(symbol)
                ratio = volume_int / avg_volume if avg_volume > 0 else 0
                
                # Parse options symbol to extract info
                option_info = self._parse_options_symbol(symbol)
                
                # Get full quote details for reporting
                bid = quote_data.get('bid', 0)
                ask = quote_data.get('ask', 0)
                last = quote_data.get('last', 0)
                open_interest = quote_data.get('open_interest', 0)
                
                unusual_event = {
                    'symbol': symbol,
                    'current_volume': volume_int,
                    'average_volume': avg_volume,
                    'volume_ratio': ratio,
                    'timestamp': timestamp,
                    'underlying': option_info.get('underlying'),
                    'option_type': option_info.get('type'),  # CALL or PUT
                    'strike': option_info.get('strike'),
                    'expiration': option_info.get('expiration'),
                    # Full quote details
                    'bid': bid,
                    'ask': ask,
                    'last': last,
                    'open_interest': open_interest,
                }
                
                self.unusual_events.append(unusual_event)
                self.unusual_detections += 1
                
                return unusual_event
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing quote for unusual volume: {e}", exc_info=True)
            return None
    
    def _parse_options_symbol(self, symbol: str) -> Dict:
        """
        Parse options symbol to extract underlying, type, strike, expiration
        
        Format: SYMBOL_YYMMDDC/P###.##
        Example: AAPL_240119C150 -> AAPL, CALL, $150, Jan 19 2024
        """
        info = {
            'underlying': None,
            'type': None,  # CALL or PUT
            'strike': None,
            'expiration': None,
        }
        
        try:
            if '_' in symbol:
                parts = symbol.split('_')
                if len(parts) >= 2:
                    info['underlying'] = parts[0]
                    
                    # Parse expiration and type
                    option_part = parts[1]
                    if len(option_part) >= 7:
                        # Format: YYMMDDC/P###
                        date_str = option_part[:6]  # YYMMDD
                        type_char = option_part[6]  # C or P
                        strike_str = option_part[7:]  # Strike price
                        
                        info['expiration'] = date_str
                        info['type'] = 'CALL' if type_char.upper() == 'C' else 'PUT'
                        
                        try:
                            info['strike'] = float(strike_str)
                        except:
                            pass
        except Exception as e:
            logger.debug(f"Could not parse options symbol {symbol}: {e}")
        
        return info
    
    def get_unusual_events_summary(self, limit: int = 50) -> Dict:
        """Get summary of unusual volume events"""
        recent_events = self.unusual_events[-limit:] if len(self.unusual_events) > limit else self.unusual_events
        
        summary = {
            'total_detections': self.unusual_detections,
            'recent_events': recent_events,
            'by_type': {'CALL': 0, 'PUT': 0},
            'by_underlying': defaultdict(int),
        }
        
        for event in recent_events:
            option_type = event.get('option_type', 'UNKNOWN')
            if option_type in summary['by_type']:
                summary['by_type'][option_type] += 1
            
            underlying = event.get('underlying')
            if underlying:
                summary['by_underlying'][underlying] += 1
        
        return summary

