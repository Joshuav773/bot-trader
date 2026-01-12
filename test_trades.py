#!/usr/bin/env python3
"""
Test Script - Get Trades from Last 4 Hours (Filter by $50 minimum)
Queries Schwab account activities and filters trades
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from schwab.auth import client_from_token_file
except ImportError:
    print("❌ Error: schwab-py not installed")
    sys.exit(1)


def format_trade(activity):
    """Format trade/order activity for display"""
    try:
        # Order fields - schwab-py orders have different structure
        # Try various field names
        symbol = 'N/A'
        quantity = 0
        price = 0
        trade_value = 0
        
        # Get symbol
        if 'symbol' in activity:
            symbol = activity['symbol']
        elif 'instrument' in activity:
            instrument = activity['instrument']
            if isinstance(instrument, dict):
                symbol = instrument.get('symbol', 'N/A')
            else:
                symbol = str(instrument)
        
        # Get order details
        order_type = activity.get('orderType', activity.get('type', 'UNKNOWN'))
        status = activity.get('status', activity.get('orderStatus', 'UNKNOWN'))
        
        # Get quantity
        quantity = activity.get('quantity', activity.get('filledQuantity', activity.get('remainingQuantity', 0)))
        if quantity == 0:
            # Try orderLegCollection
            if 'orderLegCollection' in activity:
                legs = activity['orderLegCollection']
                if legs and len(legs) > 0:
                    quantity = legs[0].get('quantity', 0)
        
        # Get price
        price = activity.get('price', activity.get('averagePrice', activity.get('stopPrice', 0)))
        if price == 0:
            # Try executionLegs
            if 'executionLegs' in activity:
                legs = activity['executionLegs']
                if legs and len(legs) > 0:
                    price = legs[0].get('price', 0)
        
        # Calculate value
        if quantity and price:
            trade_value = float(quantity) * float(price)
        elif 'orderActivityCollection' in activity:
            # Sum up execution values
            activities = activity['orderActivityCollection']
            for act in activities:
                exec_price = act.get('executionLegs', [{}])[0].get('price', 0)
                exec_qty = act.get('quantity', 0)
                if exec_price and exec_qty:
                    trade_value += float(exec_price) * float(exec_qty)
        
        # Get date
        date_str = activity.get('enteredTime', activity.get('transactionDate', activity.get('date', activity.get('time', 'N/A'))))
        
        # Get description
        instruction = activity.get('instruction', activity.get('orderType', 'N/A'))
        description = f"{instruction} {symbol}" if symbol != 'N/A' else instruction
        
        return {
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'value': trade_value,
            'type': order_type,
            'status': status,
            'date': date_str,
            'description': description,
            'raw': activity  # Keep raw for debugging
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw': activity
        }


def test_trades(min_value=50, hours=4):
    """Get trades from last N hours, filtered by minimum value"""
    print("=" * 80)
    print("🧪 SCHWAB TRADE HISTORY TEST")
    print("=" * 80)
    print(f"\n📋 Configuration:")
    print(f"   Minimum trade value: ${min_value}")
    print(f"   Time window: Last {hours} hours")
    print(f"\n⏳ Authenticating...")
    
    try:
        # Authenticate
        app_key = os.getenv("SCHWAB_APP_KEY")
        app_secret = os.getenv("SCHWAB_APP_SECRET")
        
        if not app_key or not app_secret:
            print("❌ Missing SCHWAB_APP_KEY or SCHWAB_APP_SECRET in .env")
            return False
        
        client = client_from_token_file('token.json', app_key, app_secret)
        print("✅ Authenticated")
        
        # Get account numbers
        print("\n📊 Getting account numbers...")
        try:
            accounts = client.get_account_numbers()
            if not accounts:
                print("❌ No accounts found")
                return False
            print(f"✅ Found {len(accounts)} account(s)")
            account_id = accounts[0]
            print(f"   Using account: {account_id}")
        except Exception as e:
            print(f"⚠️  Could not get account numbers: {e}")
            print("   Trying to get activities without account number...")
            account_id = None
        
        # Calculate time window
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        print(f"\n📅 Time window:")
        print(f"   From: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   To:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get orders/trades
        print("\n📈 Fetching orders...")
        try:
            activities = []
            
            # Try get_orders_for_all_linked_accounts (easiest - no account hash needed)
            if hasattr(client, 'get_orders_for_all_linked_accounts'):
                # Get orders from last 4 hours (API uses max_entries and from_entered_time)
                # Convert datetime to epoch milliseconds
                from_entered_time = int(start_time.timestamp() * 1000)
                to_entered_time = int(end_time.timestamp() * 1000)
                
                # Get orders (API might have different parameter names)
                # Try with parameters
                try:
                    result = client.get_orders_for_all_linked_accounts(
                        max_results=500,
                        from_entered_time=start_time,
                        to_entered_time=end_time
                    )
                except TypeError:
                    # Try without time parameters
                    try:
                        result = client.get_orders_for_all_linked_accounts(max_results=500)
                    except TypeError:
                        # Try with no parameters
                        result = client.get_orders_for_all_linked_accounts()
                
                # Result might be a Response object - extract data
                if hasattr(result, 'json'):
                    activities = result.json()
                elif isinstance(result, dict):
                    # Check common keys
                    if 'orders' in result:
                        activities = result['orders']
                    elif 'data' in result:
                        activities = result['data']
                    else:
                        activities = [result]
                elif isinstance(result, list):
                    activities = result
                else:
                    activities = [result] if result else []
            else:
                print("⚠️  get_orders_for_all_linked_accounts method not available")
                print("\n📋 Available methods with 'activity' or 'trade':")
                methods = [m for m in dir(client) if not m.startswith('_') and 
                          any(x in m.lower() for x in ['activity', 'trade', 'order', 'transaction'])]
                for m in sorted(methods):
                    print(f"   - {m}")
                return False
            
            if not activities:
                print(f"⚠️  No orders found")
                print("\n💡 Tip: Make sure you have executed trades/orders in your account")
                return True
            
            print(f"✅ Found {len(activities)} order(s)")
            
            # Filter by time and value
            print(f"\n🔍 Filtering orders (last {hours} hours, minimum value: ${min_value})...")
            filtered_trades = []
            
            for activity in activities:
                formatted = format_trade(activity)
                
                # Check if it's an error
                if 'error' in formatted:
                    continue
                
                # Filter by time (check if order is within time window)
                date_str = formatted.get('date', '')
                if date_str and date_str != 'N/A':
                    try:
                        # Parse date (could be ISO format, timestamp, etc.)
                        if isinstance(date_str, (int, float)):
                            order_time = datetime.fromtimestamp(date_str / 1000 if date_str > 1e10 else date_str)
                        elif isinstance(date_str, str):
                            # Try parsing ISO format
                            try:
                                order_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except:
                                try:
                                    order_time = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S')
                                except:
                                    # If can't parse, include it
                                    order_time = start_time
                        else:
                            order_time = start_time
                        
                        # Check if within time window
                        if order_time < start_time or order_time > end_time:
                            continue
                    except:
                        # If can't parse date, include it
                        pass
                
                # Check value
                value = formatted.get('value', 0)
                if value >= min_value:
                    filtered_trades.append(formatted)
            
            # Display results
            print("\n" + "=" * 80)
            print(f"📊 FILTERED TRADES (${min_value}+ from last {hours} hours)")
            print("=" * 80)
            
            if not filtered_trades:
                print(f"\n⚠️  No trades found matching criteria (last {hours} hours, ${min_value}+ value)")
                print(f"\n📋 Showing all {len(activities)} order(s) for debugging:")
                for i, activity in enumerate(activities[:10], 1):  # Show first 10
                    formatted = format_trade(activity)
                    print(f"\n   Order {i}:")
                    if 'error' not in formatted:
                        print(f"      Symbol: {formatted.get('symbol', 'N/A')}")
                        print(f"      Type: {formatted.get('type', 'N/A')}")
                        print(f"      Value: ${formatted.get('value', 0):.2f}")
                        print(f"      Date: {formatted.get('date', 'N/A')}")
                        print(f"      Description: {formatted.get('description', 'N/A')[:60]}")
                    else:
                        print(f"      Raw: {activity}")
                return True
            
            print(f"\n✅ Found {len(filtered_trades)} trade(s)\n")
            
            # Sort by date (newest first)
            filtered_trades.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Print header
            print(f"{'Date':<20} {'Symbol':<10} {'Type':<15} {'Qty':<10} {'Price':<12} {'Value':<12} {'Description'}")
            print("-" * 100)
            
            # Print trades
            total_value = 0
            for trade in filtered_trades:
                date_str = str(trade.get('date', 'N/A'))[:19]
                symbol = trade.get('symbol', 'N/A')
                activity_type = trade.get('type', 'N/A')
                qty = trade.get('quantity', 0)
                price = trade.get('price', 0)
                value = trade.get('value', 0)
                description = trade.get('description', 'N/A')[:40]
                
                print(f"{date_str:<20} {symbol:<10} {activity_type:<15} {qty:<10} ${price:<11.2f} ${value:<11.2f} {description}")
                total_value += value
            
            print("-" * 100)
            print(f"{'TOTAL':<46} ${total_value:>11.2f}")
            print("\n✅ Test completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Error fetching activities: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to show what methods are available
            print("\n📋 Checking available methods...")
            methods = [m for m in dir(client) if not m.startswith('_')]
            activity_methods = [m for m in methods if 'activity' in m.lower() or 'trade' in m.lower() or 'order' in m.lower()]
            if activity_methods:
                print("   Available methods:")
                for m in sorted(activity_methods):
                    print(f"     - {m}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Schwab trade history")
    parser.add_argument(
        "--min-value",
        type=float,
        default=50.0,
        help="Minimum trade value in USD (default: 50.0)"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=4,
        help="Number of hours to look back (default: 4)"
    )
    
    args = parser.parse_args()
    
    success = test_trades(min_value=args.min_value, hours=args.hours)
    
    if success:
        print("\n✅ Test completed!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

