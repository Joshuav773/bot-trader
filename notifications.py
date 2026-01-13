"""
Email notifications using Gmail SMTP
Sends alerts to recipients in alert_recipients table
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from db import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.warning("Database module not available - notifications will be disabled")


class NotificationService:
    """Email notification service using Gmail SMTP"""
    
    def __init__(self):
        self.smtp_server = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
        self.gmail_user = os.getenv("GMAIL_USER")
        self.gmail_password = os.getenv("GMAIL_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
        self.from_email = os.getenv("GMAIL_FROM_EMAIL") or self.gmail_user
        
        self.db = get_db() if DB_AVAILABLE else None
        self.recipients_cache = []
        self.cache_updated = None
        
        if not self.gmail_user or not self.gmail_password:
            logger.warning("Gmail credentials not configured - notifications will be disabled")
    
    def get_alert_recipients(self, use_cache: bool = True) -> List[Dict]:
        """Get alert recipients from database (email_enabled = true)"""
        if not self.db:
            return []
        
        # Use cache if fresh (updated in last 5 minutes)
        if use_cache and self.recipients_cache and self.cache_updated:
            cache_age = (datetime.now() - self.cache_updated).total_seconds()
            if cache_age < 300:  # 5 minutes
                return self.recipients_cache
        
        try:
            if not self.db.conn:
                if not self.db.connect():
                    return []
            
            cursor = self.db.conn.cursor()
            
            cursor.execute("""
                SELECT id, email, name, email_enabled
                FROM alert_recipients
                WHERE email_enabled = true
                AND email IS NOT NULL
                AND email != ''
            """)
            
            recipients = []
            for row in cursor.fetchall():
                recipients.append({
                    'id': row[0],
                    'email': row[1],
                    'name': row[2] or 'Recipient',
                    'email_enabled': row[3]
                })
            
            cursor.close()
            
            # Update cache
            self.recipients_cache = recipients
            self.cache_updated = datetime.now()
            
            logger.debug(f"📧 Loaded {len(recipients)} email recipients")
            return recipients
            
        except Exception as e:
            logger.error(f"Error getting alert recipients: {e}")
            return []
    
    def format_quote_email(self, quote: Dict) -> tuple:
        """Format quote data as email subject and body"""
        symbol = quote.get('symbol', 'N/A')
        last_price = quote.get('last', 'N/A')
        bid = quote.get('bid', 'N/A')
        ask = quote.get('ask', 'N/A')
        volume = quote.get('volume', 'N/A')
        timestamp = quote.get('timestamp', datetime.now().isoformat())
        
        # Format timestamp
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            timestamp_str = str(timestamp)
        
        # Format prices
        def fmt_price(p):
            if p is None or p == 'N/A':
                return 'N/A'
            try:
                return f"${float(p):,.2f}"
            except:
                return str(p)
        
        subject = f"📊 {symbol} Quote: {fmt_price(last_price)}"
        
        # HTML body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 10px; }}
                .content {{ padding: 20px; }}
                .quote-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                .quote-table th, .quote-table td {{ 
                    border: 1px solid #ddd; 
                    padding: 12px; 
                    text-align: left; 
                }}
                .quote-table th {{ background-color: #f2f2f2; }}
                .symbol {{ font-weight: bold; font-size: 1.2em; }}
                .price {{ font-size: 1.1em; font-weight: bold; color: #4CAF50; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 Real-Time Market Quote</h2>
            </div>
            <div class="content">
                <p>New quote received for <span class="symbol">{symbol}</span></p>
                
                <table class="quote-table">
                    <tr>
                        <th>Symbol</th>
                        <td class="symbol">{symbol}</td>
                    </tr>
                    <tr>
                        <th>Last Price</th>
                        <td class="price">{fmt_price(last_price)}</td>
                    </tr>
                    <tr>
                        <th>Bid</th>
                        <td>{fmt_price(bid)}</td>
                    </tr>
                    <tr>
                        <th>Ask</th>
                        <td>{fmt_price(ask)}</td>
                    </tr>
                    <tr>
                        <th>Volume</th>
                        <td>{volume:,}</td>
                    </tr>
                    <tr>
                        <th>Timestamp</th>
                        <td>{timestamp_str}</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
        
        # Plain text body
        text_body = f"""
Real-Time Market Quote

Symbol: {symbol}
Last Price: {fmt_price(last_price)}
Bid: {fmt_price(bid)}
Ask: {fmt_price(ask)}
Volume: {volume:,}
Timestamp: {timestamp_str}

---
Sent by Bot Trader Streamer
        """
        
        return subject, text_body, html_body
    
    def send_email(self, to_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
        """Send email using Gmail SMTP"""
        if not self.gmail_user or not self.gmail_password:
            logger.warning("Gmail credentials not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text and HTML
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)
            
            if html_body:
                part2 = MIMEText(html_body, 'html')
                msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_user, self.gmail_password)
                server.send_message(msg)
            
            logger.debug(f"📧 Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def send_quote_notification(self, quote: Dict) -> int:
        """Send quote notification to all enabled recipients"""
        if not self.gmail_user or not self.gmail_password:
            return 0
        
        recipients = self.get_alert_recipients()
        if not recipients:
            logger.debug("No email recipients found")
            return 0
        
        subject, text_body, html_body = self.format_quote_email(quote)
        
        sent = 0
        for recipient in recipients:
            email = recipient.get('email')
            if email:
                if self.send_email(email, subject, text_body, html_body):
                    sent += 1
        
        if sent > 0:
            logger.info(f"📧 Sent quote notification to {sent} recipient(s)")
        
        return sent


# Global notification service instance
_notification_service = None

def get_notification_service() -> NotificationService:
    """Get notification service instance (singleton)"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

