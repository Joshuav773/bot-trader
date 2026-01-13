#!/usr/bin/env python3
"""
Quick test script for email notifications
Tests Gmail SMTP connection and sends a test email
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

def test_email_config():
    """Test Gmail configuration"""
    print("=" * 80)
    print("🧪 TESTING GMAIL EMAIL CONFIGURATION")
    print("=" * 80)
    print()
    
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
    
    print("📋 Configuration Check:")
    print(f"   GMAIL_USER: {'✅ Set' if gmail_user else '❌ Missing'}")
    if gmail_user:
        print(f"      Value: {gmail_user}")
    
    print(f"   GMAIL_PASSWORD: {'✅ Set' if gmail_password else '❌ Missing'}")
    if gmail_password:
        masked = '*' * (len(gmail_password) - 4) + gmail_password[-4:] if len(gmail_password) > 4 else '****'
        print(f"      Value: {masked} (masked)")
    
    print()
    
    if not gmail_user or not gmail_password:
        print("❌ Missing Gmail configuration!")
        print()
        print("💡 Add to .env file:")
        print("   GMAIL_USER=your-email@gmail.com")
        print("   GMAIL_PASSWORD=your-app-password")
        print()
        print("📋 Get App Password:")
        print("   1. Enable 2-Step Verification: https://myaccount.google.com/security")
        print("   2. Create App Password: https://myaccount.google.com/apppasswords")
        return False
    
    # Test SMTP connection
    print("📡 Testing SMTP connection...")
    try:
        import smtplib
        
        smtp_server = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
        
        print(f"   Server: {smtp_server}")
        print(f"   Port: {smtp_port}")
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        
        print("   Attempting login...")
        server.login(gmail_user, gmail_password)
        server.quit()
        
        print("✅ SMTP connection successful!")
        print()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print()
        print("💡 Common issues:")
        print("   - Using regular password instead of App Password")
        print("   - 2-Step Verification not enabled")
        print("   - App Password incorrect or expired")
        print()
        print("📋 Get App Password:")
        print("   https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("💡 Check your internet connection and Gmail settings")
        return False


def test_send_email():
    """Test sending a test email"""
    print("=" * 80)
    print("📧 TESTING EMAIL SEND")
    print("=" * 80)
    print()
    
    try:
        from notifications import get_notification_service
        
        notification_service = get_notification_service()
        
        # Check if we have a test recipient
        recipients = notification_service.get_alert_recipients(use_cache=False)
        if not recipients:
            print("⚠️  No recipients found in alert_recipients table")
            print()
            print("💡 Add a test recipient:")
            print("   INSERT INTO alert_recipients (email, email_enabled, created_at, updated_at)")
            print("   VALUES ('your-email@gmail.com', true, NOW(), NOW());")
            print()
            return False
        
        print(f"📋 Found {len(recipients)} recipient(s):")
        for recipient in recipients:
            print(f"   - {recipient.get('email')} ({recipient.get('name')})")
        print()
        
        # Create test quote
        test_quote = {
            'symbol': 'TEST',
            'timestamp': '2024-01-12T12:00:00Z',
            'last': 100.50,
            'bid': 100.49,
            'ask': 100.51,
            'volume': 123456,
            'bid_size': 100,
            'ask_size': 200
        }
        
        print("📤 Sending test email...")
        sent = notification_service.send_quote_notification(test_quote)
        
        if sent > 0:
            print(f"✅ Test email sent successfully to {sent} recipient(s)!")
            print()
            print("💡 Check your inbox (and spam folder)")
            return True
        else:
            print("❌ Failed to send test email")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    # Test configuration
    if not test_email_config():
        sys.exit(1)
    
    print()
    
    # Test sending email
    if test_send_email():
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Email send test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

