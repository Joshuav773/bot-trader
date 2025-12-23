"""
Test script for email and SMS alerts.

This sends a test alert to verify your email/SMS configuration is working.
"""
import logging
from datetime import datetime, timezone
from sqlmodel import Session

from order_flow.alerts import get_alert_service
from api.models import OrderFlow
from api.db import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def test_alerts():
    """Test sending alerts to all configured recipients."""
    print("=" * 70)
    print("🧪 Testing Alert System")
    print("=" * 70)
    print()
    
    # Create a test order
    test_order = OrderFlow(
        ticker="AAPL",
        display_ticker="AAPL",
        order_type="buy",
        order_side="buy",
        instrument="equity",
        order_size_usd=750000.00,  # Above $500k threshold
        price=150.00,
        size=5000,
        timestamp=datetime.now(timezone.utc),
        source="test",
    )
    
    print("Test order created:")
    print(f"  Ticker: {test_order.ticker}")
    print(f"  Size: ${test_order.order_size_usd:,.2f}")
    print(f"  Price: ${test_order.price:.2f}")
    print()
    
    # Get alert service
    alert_service = get_alert_service()
    
    print("Sending test alerts...")
    print()
    
    try:
        results = alert_service.send_trade_alert(test_order)
        
        print("=" * 70)
        print("✅ Alert Results")
        print("=" * 70)
        print(f"  Email sent: {results.get('email_sent', False)}")
        print(f"  Email count: {results.get('email_count', 0)}")
        print(f"  SMS sent: {results.get('sms_sent', False)}")
        print(f"  SMS count: {results.get('sms_count', 0)}")
        print()
        
        if results.get('email_sent'):
            print("✅ Email alerts sent successfully!")
            print(f"   Check inboxes for: joshuav773@gmail.com, jelberrios009@yahoo.com")
        else:
            print("❌ Email alerts failed")
            print("   Check your email configuration in .env")
        
        if results.get('sms_sent'):
            print("✅ SMS alerts sent successfully!")
        else:
            print("⚠️  SMS alerts not sent (may not be configured)")
        
        print()
        return results.get('email_sent') or results.get('sms_sent')
        
    except Exception as e:
        print(f"❌ Error sending alerts: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_alerts()
    if success:
        print("=" * 70)
        print("✅ Test completed successfully!")
        print("=" * 70)
    else:
        print("=" * 70)
        print("❌ Test failed - check your configuration")
        print("=" * 70)
        exit(1)

