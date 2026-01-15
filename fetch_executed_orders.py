"""
Fetch Executed Orders from Schwab Account API
=============================================

Fetches already executed/filled orders from your Schwab account API.
These are orders that have ALREADY been executed - no waiting, no streaming.

Shows: Symbol, Side (BUY/SELL), Size, Price, Execution Time, Order Type

Usage:
    python3 fetch_executed_orders.py AAPL 30
    python3 fetch_executed_orders.py TSLA 50
"""
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from schwab.auth import client_from_token_file
    SCHWAB_AVAILABLE = True
except ImportError:
    SCHWAB_AVAILABLE = False
    logger.error("schwab-py not installed. Run: pip install schwab-py")


def get_executed_orders(client, symbol: str, limit: int = 30):
    """Get executed orders from account API"""
    orders = []
    
    try:
        # Try different methods to get executed orders
        methods_to_try = [
            ('get_orders_for_all_linked_accounts', {}),
            ('get_all_orders', {}),
            ('get_orders', {}),
        ]
        
        for method_name, params in methods_to_try:
            if hasattr(client, method_name):
                try:
                    method = getattr(client, method_name)
                    logger.info(f"   Trying {method_name}...")
                    
                    # Try with different parameters
                    try:
                        # Get more orders to filter
                        result = method(max_results=limit * 10)
                    except TypeError:
                        try:
                            result = method()
                        except:
                            continue
                    
                    # Handle response
                    if hasattr(result, 'json'):
                        data = result.json()
                    elif hasattr(result, 'status_code'):
                        if result.status_code == 200:
                            data = result.json()
                        else:
                            continue
                    elif isinstance(result, dict):
                        data = result
                    elif isinstance(result, list):
                        data = {'orders': result}
                    else:
                        continue
                    
                    # Extract orders
                    all_orders = data.get('orders', data.get('data', data.get('items', [])))
                    
                    if all_orders:
                        logger.info(f"   ✅ Found {len(all_orders)} total orders")
                        
                        # Filter for symbol and executed status
                        for order in all_orders:
                            if not isinstance(order, dict):
                                continue
                            
                            # Check status - only executed/filled orders
                            status = order.get('status', '').upper()
                            if status not in ['FILLED', 'EXECUTED', 'PARTIAL']:
                                continue
                            
                            # Get symbol
                            order_symbol = (
                                order.get('symbol', '') or
                                order.get('instrument', {}).get('symbol', '') or
                                order.get('underlyingSymbol', '')
                            )
                            
                            if not order_symbol:
                                continue
                            
                            # Check if matches (handle options symbols)
                            if order_symbol.upper().startswith(symbol.upper()):
                                # Extract execution details
                                executions = order.get('executionLegs', order.get('executions', []))
                                
                                if executions:
                                    # Multiple executions for this order
                                    for exec in executions:
                                        exec_time = exec.get('time', order.get('enteredTime', order.get('closeTime')))
                                        exec_price = float(exec.get('price', order.get('price', 0)))
                                        exec_quantity = int(exec.get('quantity', exec.get('size', order.get('quantity', 0))))
                                        
                                        # Determine option type if applicable
                                        option_type = None
                                        if 'PUT' in order_symbol.upper() or 'P' in order_symbol[-1:]:
                                            option_type = 'PUT'
                                        elif 'CALL' in order_symbol.upper() or 'C' in order_symbol[-1:]:
                                            option_type = 'CALL'
                                        
                                        order_data = {
                                            'symbol': order_symbol.upper(),
                                            'timestamp': exec_time,
                                            'order_side': order.get('instruction', order.get('side', 'UNKNOWN')).upper(),
                                            'size': exec_quantity,
                                            'price': exec_price,
                                            'value': exec_price * exec_quantity,
                                            'order_type': 'OPTION' if option_type else 'STOCK',
                                            'option_type': option_type,
                                            'status': status,
                                        }
                                        orders.append(order_data)
                                else:
                                    # Single execution - use order data
                                    exec_time = order.get('enteredTime', order.get('closeTime', order.get('transactionDate')))
                                    exec_price = float(order.get('price', order.get('averagePrice', order.get('stopPrice', 0))))
                                    exec_quantity = int(order.get('quantity', order.get('filledQuantity', 0)))
                                    
                                    # Determine option type
                                    option_type = None
                                    if 'PUT' in order_symbol.upper() or 'P' in order_symbol[-1:]:
                                        option_type = 'PUT'
                                    elif 'CALL' in order_symbol.upper() or 'C' in order_symbol[-1:]:
                                        option_type = 'CALL'
                                    
                                    order_data = {
                                        'symbol': order_symbol.upper(),
                                        'timestamp': exec_time,
                                        'order_side': order.get('instruction', order.get('side', 'UNKNOWN')).upper(),
                                        'size': exec_quantity,
                                        'price': exec_price,
                                        'value': exec_price * exec_quantity,
                                        'order_type': 'OPTION' if option_type else 'STOCK',
                                        'option_type': option_type,
                                        'status': status,
                                    }
                                    orders.append(order_data)
                        
                        if orders:
                            # Sort by timestamp (most recent first), limit to N
                            orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                            return orders[:limit]
                
                except Exception as e:
                    logger.debug(f"   {method_name} failed: {e}")
                    continue
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting executed orders: {e}", exc_info=True)
        return []


def display_orders(orders: list, symbol: str):
    """Display executed orders in formatted table"""
    if not orders:
        logger.info("")
        logger.info("=" * 120)
        logger.info("❌ NO EXECUTED ORDERS FOUND")
        logger.info("=" * 120)
        logger.info("")
        logger.info("Possible reasons:")
        logger.info("  • No executed orders for this symbol in your account")
        logger.info("  • Orders are pending/cancelled (only FILLED orders are shown)")
        logger.info("  • Symbol not found in order history")
        logger.info("")
        logger.info("Note: This fetches orders from YOUR account, not market-wide orders")
        return
    
    logger.info("")
    logger.info("=" * 120)
    logger.info(f"📊 LAST {len(orders)} EXECUTED ORDERS - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("These are ALREADY EXECUTED orders from your account (not live streaming)")
    logger.info("")
    logger.info(f"{'#':<4} {'Time':<22} {'Side':<6} {'Size':<12} {'Price':<12} {'Value (USD)':<15} {'Type':<10}")
    logger.info("-" * 120)
    
    for i, order in enumerate(orders, 1):
        timestamp = order.get('timestamp', '')
        
        # Format timestamp
        if isinstance(timestamp, str):
            try:
                # Try parsing different formats
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                timestamp_str = str(timestamp)[:19]
        elif isinstance(timestamp, datetime):
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp_str = str(timestamp)[:19]
        
        side = order.get('order_side', 'UNKNOWN')
        size = order.get('size', 0)
        price = order.get('price', 0)
        value = order.get('value', 0)
        order_type = order.get('order_type', 'STOCK')
        option_type = order.get('option_type')
        
        type_str = f"{order_type}"
        if option_type:
            type_str = f"{option_type}"
        
        print(f"{i:2d}.  {timestamp_str:<22} {side:<6} {size:>10,}  ${price:>10.4f}  ${value:>13,.2f}  {type_str:<10}")
    
    logger.info("-" * 120)
    
    # Summary
    total_value = sum(o.get('value', 0) for o in orders)
    total_size = sum(o.get('size', 0) for o in orders)
    buy_orders = [o for o in orders if 'BUY' in o.get('order_side', '').upper()]
    sell_orders = [o for o in orders if 'SELL' in o.get('order_side', '').upper()]
    stock_orders = [o for o in orders if o.get('order_type') == 'STOCK']
    option_orders = [o for o in orders if o.get('order_type') == 'OPTION']
    prices = [o.get('price', 0) for o in orders if o.get('price', 0) > 0]
    
    logger.info("")
    logger.info("📈 Summary:")
    logger.info(f"   Total executed orders: {len(orders)}")
    logger.info(f"   BUY orders: {len(buy_orders)}")
    logger.info(f"   SELL orders: {len(sell_orders)}")
    logger.info(f"   Stock orders: {len(stock_orders)}")
    logger.info(f"   Option orders: {len(option_orders)}")
    logger.info(f"   Total size: {total_size:,} shares/contracts")
    logger.info(f"   Total value: ${total_value:,.2f}")
    if prices:
        logger.info(f"   Price range: ${min(prices):.4f} - ${max(prices):.4f}")
    logger.info("")
    logger.info("=" * 120)
    logger.info("✅ Data from Schwab Account API (Executed Orders)")
    logger.info("=" * 120)
    logger.info("")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch already executed orders from Schwab Account API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_executed_orders.py AAPL 30
  python3 fetch_executed_orders.py TSLA 50
        """
    )
    parser.add_argument(
        'symbol',
        help='Stock symbol (e.g., AAPL, TSLA, NVDA)'
    )
    parser.add_argument(
        'limit',
        type=int,
        nargs='?',
        default=30,
        help='Number of orders to fetch (default: 30)'
    )
    
    args = parser.parse_args()
    
    if not SCHWAB_AVAILABLE:
        logger.error("schwab-py library not available")
        return 1
    
    symbol = args.symbol.upper()
    limit = args.limit
    
    logger.info("=" * 120)
    logger.info(f"🔍 FETCHING LAST {limit} EXECUTED ORDERS - {symbol}")
    logger.info("=" * 120)
    logger.info("")
    logger.info("This fetches ALREADY EXECUTED orders from your account (no waiting, no streaming)")
    logger.info("Shows: Symbol, Side (BUY/SELL), Size, Price, Execution Time, PUT/CALL (if options)")
    logger.info("")
    
    try:
        app_key = os.getenv("SCHWAB_APP_KEY")
        app_secret = os.getenv("SCHWAB_APP_SECRET")
        
        if not app_key or not app_secret:
            logger.error("SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in .env")
            return 1
        
        token_path = Path("token.json")
        if not token_path.exists():
            logger.error("token.json not found. Run schwab_streamer.py first to authenticate.")
            return 1
        
        logger.info("🔐 Authenticating...")
        client = client_from_token_file(
            token_path=str(token_path),
            app_secret=app_secret,
            api_key=app_key,
        )
        logger.info("✅ Authenticated")
        logger.info("")
        
        logger.info(f"📡 Fetching last {limit} executed orders for {symbol}...")
        orders = get_executed_orders(client, symbol, limit=limit)
        
        display_orders(orders, symbol)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())


