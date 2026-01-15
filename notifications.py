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
    
    def send_large_trade_notification(self, trade: Dict) -> int:
        """Send large trade notification to all enabled recipients"""
        if not self.gmail_user or not self.gmail_password:
            return 0
        
        recipients = self.get_alert_recipients()
        if not recipients:
            logger.debug("No email recipients found")
            return 0
        
        subject, text_body, html_body = self.format_trade_email(trade)
        
        sent = 0
        for recipient in recipients:
            email = recipient.get('email')
            if email:
                if self.send_email(email, subject, text_body, html_body):
                    sent += 1
        
        if sent > 0:
            logger.info(f"📧 Sent large trade notification to {sent} recipient(s)")
        
        return sent
    
    def format_trade_email(self, trade: Dict) -> tuple:
        """Format large trade data as email subject and body"""
        symbol = trade.get('symbol', 'N/A')
        trade_value_usd = trade.get('trade_value_usd', 0)
        entry_price = trade.get('entry_price', 'N/A')
        exit_price = trade.get('exit_price', 'N/A')
        volume = trade.get('volume', 0)
        price_change = trade.get('price_change', 0)
        price_change_pct = trade.get('price_change_pct', 0)
        timestamp = trade.get('exit_time', trade.get('timestamp', datetime.now()))
        
        # Format timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Format prices
        def fmt_price(p):
            if p is None or p == 'N/A':
                return 'N/A'
            try:
                return f"${float(p):,.2f}"
            except:
                return str(p)
        
        subject = f"💰 Large Trade Alert: {symbol} - {fmt_price(trade_value_usd)}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #4CAF50; color: white; padding: 10px; }}
                .content {{ padding: 20px; }}
                .trade-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                .trade-table th, .trade-table td {{ 
                    border: 1px solid #ddd; 
                    padding: 12px; 
                    text-align: left; 
                }}
                .trade-table th {{ background-color: #f2f2f2; }}
                .symbol {{ font-weight: bold; font-size: 1.2em; }}
                .value {{ font-size: 1.1em; font-weight: bold; color: #4CAF50; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>💰 Large Trade Alert</h2>
            </div>
            <div class="content">
                <p>A significant trade has been executed for <span class="symbol">{symbol}</span>.</p>
                
                <table class="trade-table">
                    <tr>
                        <th>Symbol</th>
                        <td class="symbol">{symbol}</td>
                    </tr>
                    <tr>
                        <th>Trade Value</th>
                        <td class="value">{fmt_price(trade_value_usd)}</td>
                    </tr>
                    <tr>
                        <th>Entry Price</th>
                        <td>{fmt_price(entry_price)}</td>
                    </tr>
                    <tr>
                        <th>Exit Price</th>
                        <td>{fmt_price(exit_price)}</td>
                    </tr>
                    <tr>
                        <th>Volume</th>
                        <td>{volume:,} shares</td>
                    </tr>
                    <tr>
                        <th>Price Change</th>
                        <td>{fmt_price(price_change)} ({price_change_pct:+.2f}%)</td>
                    </tr>
                    <tr>
                        <th>Timestamp</th>
                        <td>{timestamp_str}</td>
                    </tr>
                </table>
                
                <p>This alert is generated by your Bot Trader streaming service.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Large Trade Alert: {symbol} - {fmt_price(trade_value_usd)}

A significant trade has been executed for {symbol}.

Symbol: {symbol}
Trade Value: {fmt_price(trade_value_usd)}
Entry Price: {fmt_price(entry_price)}
Exit Price: {fmt_price(exit_price)}
Volume: {volume:,} shares
Price Change: {fmt_price(price_change)} ({price_change_pct:+.2f}%)
Timestamp: {timestamp_str}

This alert is generated by your Bot Trader streaming service.
        """
        
        return subject, text_body, html_body
    
    def format_order_email(self, order: Dict) -> tuple:
        """Format large order data as email subject and body"""
        symbol = order.get('symbol', 'N/A')
        order_type = order.get('order_type', 'UNKNOWN')
        order_value = order.get('order_value_usd', 0)
        order_size = order.get('order_size_shares', 0)
        price = order.get('price', 'N/A')
        spread = order.get('spread')
        instrument = order.get('instrument', 'equity')
        timestamp = order.get('timestamp', datetime.now())
        
        # Format timestamp
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Format prices
        def fmt_price(p):
            if p is None or p == 'N/A':
                return 'N/A'
            try:
                return f"${float(p):,.2f}"
            except:
                return str(p)
        
        subject = f"🚨 Large {order_type} Order: {symbol} - {fmt_price(order_value)}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #FFC107; color: black; padding: 10px; }}
                .content {{ padding: 20px; }}
                .order-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                .order-table th, .order-table td {{ 
                    border: 1px solid #ddd; 
                    padding: 12px; 
                    text-align: left; 
                }}
                .order-table th {{ background-color: #f2f2f2; }}
                .symbol {{ font-weight: bold; font-size: 1.2em; }}
                .value {{ font-size: 1.1em; font-weight: bold; color: #FFC107; }}
                .buy {{ color: green; font-weight: bold; }}
                .sell {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 Large Order Alert</h2>
            </div>
            <div class="content">
                <p>A large {order_type.lower()} order has been detected for <span class="symbol">{symbol}</span>.</p>
                
                <table class="order-table">
                    <tr>
                        <th>Symbol</th>
                        <td class="symbol">{symbol}</td>
                    </tr>
                    <tr>
                        <th>Order Type</th>
                        <td class="{order_type.lower()}">{order_type}</td>
                    </tr>
                    <tr>
                        <th>Order Value</th>
                        <td class="value">{fmt_price(order_value)}</td>
                    </tr>
                    <tr>
                        <th>Order Size</th>
                        <td>{order_size:,} shares</td>
                    </tr>
                    <tr>
                        <th>Price</th>
                        <td>{fmt_price(price)}</td>
                    </tr>
                    <tr>
                        <th>Bid Size</th>
                        <td>{order.get('bid_size', 0) if isinstance(order.get('bid_size'), (int, float)) else 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Ask Size</th>
                        <td>{order.get('ask_size', 0) if isinstance(order.get('ask_size'), (int, float)) else 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Spread</th>
                        <td>{fmt_price(spread)}</td>
                    </tr>
                    <tr>
                        <th>Instrument</th>
                        <td>{instrument}</td>
                    </tr>
                    <tr>
                        <th>Timestamp</th>
                        <td>{timestamp_str}</td>
                    </tr>
                </table>
                
                <p>This alert is generated by your Bot Trader streaming service.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
Large Order Alert: {symbol} - {fmt_price(order_value)}

A large {order_type.lower()} order has been detected for {symbol}.

Symbol: {symbol}
Order Type: {order_type}
Order Value: {fmt_price(order_value)}
Order Size: {order_size:,} shares
Price: {fmt_price(price)}
Bid Size: {order.get('bid_size', 0) if isinstance(order.get('bid_size'), (int, float)) else 'N/A'}
Ask Size: {order.get('ask_size', 0) if isinstance(order.get('ask_size'), (int, float)) else 'N/A'}
Spread: {fmt_price(spread)}
Instrument: {instrument}
Timestamp: {timestamp_str}

This alert is generated by your Bot Trader streaming service.
        """
        
        return subject, text_body, html_body
    
    def send_order_notification(self, order: Dict) -> int:
        """Send large order notification to all enabled recipients"""
        if not self.gmail_user or not self.gmail_password:
            return 0
        
        recipients = self.get_alert_recipients()
        if not recipients:
            logger.debug("No email recipients found")
            return 0
        
        subject, text_body, html_body = self.format_order_email(order)
        
        sent = 0
        for recipient in recipients:
            email = recipient.get('email')
            if email:
                if self.send_email(email, subject, text_body, html_body):
                    sent += 1
        
        if sent > 0:
            logger.info(f"📧 Sent order notification to {sent} recipient(s)")
        
        return sent


# Global notification service instance
_notification_service = None

def get_notification_service() -> NotificationService:
    """Get notification service instance (singleton)"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

