"""
Enhanced Order Tracker - Multi-Signal Detection
================================================

Detects large orders using multiple signals:
1. Bid/Ask size changes (when orders are placed)
2. Volume spikes (sudden volume increases)
3. Price impact (price moves with volume)
4. Combined signals (multiple indicators together)

This catches more large orders than single-signal detection.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LargeOrderTracker:
    """Enhanced order tracker with multi-signal detection"""
    
    def __init__(self, min_order_value: float = 50000.0):
        """
        Initialize enhanced order tracker
        
        Args:
            min_order_value: Minimum order value in USD to trigger alert
        """
        self.min_order_value = min_order_value
        
        # Track last values per symbol
        self.last_bid_size = {}
        self.last_ask_size = {}
        self.last_bid_price = {}
        self.last_ask_price = {}
        self.last_price = {}
        self.last_volume = {}
        self.last_quote_time = {}
        
        # Deduplication: Track recent orders to avoid duplicates
        self.recent_orders = defaultdict(lambda: deque(maxlen=10))  # Last 10 orders per symbol
        self.deduplication_window_seconds = 5  # Don't alert on same order within 5 seconds
        
        # Statistics
        self.orders_detected = 0
        self.duplicates_ignored = 0
    
    def _is_duplicate(self, symbol: str, order_side: str, size: int, price: float, timestamp: datetime) -> bool:
        """Check if this order was recently detected (deduplication)"""
        recent = self.recent_orders[symbol]
        
        # Check last 5 seconds
        for prev_order in recent:
            time_diff = (timestamp - prev_order['timestamp']).total_seconds()
            if time_diff < self.deduplication_window_seconds:
                # Same side and similar size/price = likely duplicate
                if (prev_order['side'] == order_side and
                    abs(prev_order['size'] - size) < size * 0.2 and  # Within 20% size
                    abs(prev_order['price'] - price) < price * 0.01):  # Within 1% price
                    return True
        
        # Not a duplicate - add to recent orders
        recent.append({
            'side': order_side,
            'size': size,
            'price': price,
            'timestamp': timestamp
        })
        return False
    
    def process_quote(self, quote_data: Dict) -> Optional[Dict]:
        """
        Process incoming quote with multi-signal detection
        
        Args:
            quote_data: Quote data with symbol, bid, ask, bid_size, ask_size, last, volume
        
        Returns:
            Large order data if detected, otherwise None
        """
        symbol = quote_data.get('symbol')
        if not symbol:
            return None
        
        bid = quote_data.get('bid')
        ask = quote_data.get('ask')
        bid_size = quote_data.get('bid_size')
        ask_size = quote_data.get('ask_size')
        last_price = quote_data.get('last')
        volume = quote_data.get('volume')
        timestamp = datetime.fromisoformat(quote_data['timestamp'].replace('Z', '+00:00'))
        
        # Convert to floats/ints
        try:
            bid = float(bid) if bid is not None else None
            ask = float(ask) if ask is not None else None
            bid_size = int(bid_size) if bid_size is not None else 0
            ask_size = int(ask_size) if ask_size is not None else 0
            last_price = float(last_price) if last_price is not None else None
            volume = int(volume) if volume is not None else 0
        except (ValueError, TypeError):
            return None
        
        # Use last price or mid-price for valuation
        reference_price = last_price or ((bid + ask) / 2 if (bid and ask) else None)
        if not reference_price:
            return None
        
        # Initialize tracking for symbol
        if symbol not in self.last_bid_size:
            self.last_bid_size[symbol] = bid_size
            self.last_ask_size[symbol] = ask_size
            self.last_bid_price[symbol] = bid
            self.last_ask_price[symbol] = ask
            self.last_price[symbol] = reference_price
            self.last_volume[symbol] = volume
            self.last_quote_time[symbol] = timestamp
            return None
        
        # ============================================
        # MULTI-SIGNAL DETECTION
        # ============================================
        
        # Signal 1: Bid/Ask size changes (order placed)
        bid_size_delta = bid_size - self.last_bid_size[symbol]
        ask_size_delta = ask_size - self.last_ask_size[symbol]
        
        # Signal 2: Volume spike (order executed)
        volume_delta = volume - self.last_volume[symbol]
        volume_spike = volume_delta > 0
        
        # Signal 3: Price impact (price moved significantly)
        price_change = abs(reference_price - self.last_price[symbol]) if self.last_price[symbol] else 0
        price_change_pct = (price_change / self.last_price[symbol] * 100) if self.last_price[symbol] else 0
        significant_price_move = price_change_pct > 0.1  # >0.1% move
        
        # Time since last quote (to detect rapid changes)
        time_since_last = (timestamp - self.last_quote_time[symbol]).total_seconds()
        
        # ============================================
        # DETECTION LOGIC
        # ============================================
        
        detected_order = None
        order_side = None
        order_size = 0
        detection_method = None
        
        # Method 1: Large bid size increase (BUY order placed)
        if bid_size_delta > 0:
            order_value = bid_size_delta * (bid or reference_price)
            if order_value >= self.min_order_value:
                order_side = 'BUY'
                order_size = bid_size_delta
                detection_method = 'BID_SIZE_INCREASE'
                detected_order = {
                    'symbol': symbol,
                    'order_type': 'BUY_ORDER',
                    'order_side': 'BUY',
                    'order_value_usd': order_value,
                    'price': bid or reference_price,
                    'order_size_shares': bid_size_delta,
                    'timestamp': timestamp,
                    'instrument': 'equity',
                    'detection_method': detection_method,
                    'bid_size': bid_size,
                    'ask_size': ask_size,
                    'spread': (ask - bid) if (bid and ask) else None,
                }
        
        # Method 2: Large ask size increase (SELL order placed)
        if ask_size_delta > 0:
            order_value = ask_size_delta * (ask or reference_price)
            if order_value >= self.min_order_value:
                # Use this if larger or no bid order detected
                if not detected_order or order_value > detected_order.get('order_value_usd', 0):
                    order_side = 'SELL'
                    order_size = ask_size_delta
                    detection_method = 'ASK_SIZE_INCREASE'
                    detected_order = {
                        'symbol': symbol,
                        'order_type': 'SELL_ORDER',
                        'order_side': 'SELL',
                        'order_value_usd': order_value,
                        'price': ask or reference_price,
                        'order_size_shares': ask_size_delta,
                        'timestamp': timestamp,
                        'instrument': 'equity',
                        'detection_method': detection_method,
                        'bid_size': bid_size,
                        'ask_size': ask_size,
                        'spread': (ask - bid) if (bid and ask) else None,
                    }
        
        # Method 3: Volume spike with price impact (large order executed)
        if volume_spike and volume_delta > 0 and significant_price_move:
            # Determine side based on price direction
            if reference_price > self.last_price[symbol]:
                order_side_candidate = 'BUY'
            elif reference_price < self.last_price[symbol]:
                order_side_candidate = 'SELL'
            else:
                order_side_candidate = None
            
            if order_side_candidate:
                order_value = volume_delta * reference_price
                if order_value >= self.min_order_value:
                    # Use this if no order detected yet, or if value is significantly larger
                    if not detected_order or order_value > detected_order.get('order_value_usd', 0) * 1.5:
                        order_side = order_side_candidate
                        order_size = volume_delta
                        detection_method = 'VOLUME_SPIKE_WITH_PRICE_IMPACT'
                        detected_order = {
                            'symbol': symbol,
                            'order_type': f'{order_side_candidate}_ORDER',
                            'order_side': order_side_candidate,
                            'order_value_usd': order_value,
                            'price': reference_price,
                            'order_size_shares': volume_delta,
                            'timestamp': timestamp,
                            'instrument': 'equity',
                            'detection_method': detection_method,
                            'volume': volume_delta,
                            'price_change': price_change,
                            'price_change_pct': price_change_pct,
                            'bid_size': bid_size,
                            'ask_size': ask_size,
                        }
        
        # Method 4: Large volume spike at same price (order executed, no price impact)
        if volume_spike and volume_delta > 0 and not significant_price_move:
            order_value = volume_delta * reference_price
            if order_value >= self.min_order_value:
                # Use bid/ask imbalance to determine side
                if bid_size > ask_size * 1.5:  # More buy interest
                    order_side_candidate = 'BUY'
                elif ask_size > bid_size * 1.5:  # More sell interest
                    order_side_candidate = 'SELL'
                else:
                    order_side_candidate = 'EXECUTED'
                
                # Use this if no order detected or if significantly larger
                if not detected_order or order_value > detected_order.get('order_value_usd', 0) * 2:
                    order_side = order_side_candidate
                    order_size = volume_delta
                    detection_method = 'VOLUME_SPIKE_NO_PRICE_IMPACT'
                    detected_order = {
                        'symbol': symbol,
                        'order_type': f'{order_side_candidate}_ORDER' if order_side_candidate != 'EXECUTED' else 'LARGE_TRADE',
                        'order_side': order_side_candidate,
                        'order_value_usd': order_value,
                        'price': reference_price,
                        'order_size_shares': volume_delta,
                        'timestamp': timestamp,
                        'instrument': 'equity',
                        'detection_method': detection_method,
                        'volume': volume_delta,
                        'bid_size': bid_size,
                        'ask_size': ask_size,
                    }
        
        # Method 5: Combined signal (size change + volume spike + price move)
        if (bid_size_delta > 0 or ask_size_delta > 0) and volume_spike and significant_price_move:
            # Strong signal - multiple indicators
            combined_size = max(bid_size_delta, ask_size_delta)
            combined_volume = volume_delta
            
            # Use the larger of size change or volume
            use_size = combined_size if combined_size > combined_volume * 0.5 else combined_volume
            
            if bid_size_delta > ask_size_delta:
                order_side_candidate = 'BUY'
                order_price = bid or reference_price
            else:
                order_side_candidate = 'SELL'
                order_price = ask or reference_price
            
            order_value = use_size * order_price
            if order_value >= self.min_order_value:
                # This is a very strong signal - use it if better
                if not detected_order or order_value > detected_order.get('order_value_usd', 0) * 1.2:
                    order_side = order_side_candidate
                    order_size = use_size
                    detection_method = 'COMBINED_SIGNAL'
                    detected_order = {
                        'symbol': symbol,
                        'order_type': f'{order_side_candidate}_ORDER',
                        'order_side': order_side_candidate,
                        'order_value_usd': order_value,
                        'price': order_price,
                        'order_size_shares': use_size,
                        'timestamp': timestamp,
                        'instrument': 'equity',
                        'detection_method': detection_method,
                        'bid_size_delta': bid_size_delta,
                        'ask_size_delta': ask_size_delta,
                        'volume_delta': volume_delta,
                        'price_change_pct': price_change_pct,
                        'bid_size': bid_size,
                        'ask_size': ask_size,
                    }
        
        # Update tracking (always update, even if no order detected)
        self.last_bid_size[symbol] = bid_size
        self.last_ask_size[symbol] = ask_size
        self.last_bid_price[symbol] = bid
        self.last_ask_price[symbol] = ask
        self.last_price[symbol] = reference_price
        self.last_volume[symbol] = volume
        self.last_quote_time[symbol] = timestamp
        
        # Return detected order if found and not duplicate
        if detected_order:
            # Deduplication check
            if self._is_duplicate(symbol, order_side, order_size, detected_order['price'], timestamp):
                self.duplicates_ignored += 1
                logger.debug(f"Duplicate order ignored: {symbol} {order_side} {order_size:,} @ ${detected_order['price']:.2f}")
                return None
            
            self.orders_detected += 1
            logger.debug(f"Order detected via {detection_method}: {symbol} {order_side} ${detected_order['order_value_usd']:,.2f}")
            return detected_order
        
        return None
    
    def get_stats(self) -> Dict:
        """Get tracking statistics"""
        return {
            'symbols_tracked': len(self.last_bid_size),
            'min_order_value': self.min_order_value,
            'orders_detected': self.orders_detected,
            'duplicates_ignored': self.duplicates_ignored,
        }
