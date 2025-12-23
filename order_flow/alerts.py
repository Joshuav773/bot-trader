"""
Real-time alert system for large trades.

Supports:
- Email alerts (SMTP - Gmail, SendGrid, etc.)
- SMS alerts (Twilio, email-to-SMS gateways)
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
from datetime import datetime

import requests

from sqlmodel import select, Session

from api.models import OrderFlow, AlertRecipient
from api.db import engine
from config.settings import (
    ALERT_EMAIL_ENABLED,
    ALERT_EMAIL_SMTP_HOST,
    ALERT_EMAIL_SMTP_PORT,
    ALERT_EMAIL_SMTP_USER,
    ALERT_EMAIL_SMTP_PASSWORD,
    ALERT_EMAIL_FROM,
    ALERT_EMAIL_TO,
    ALERT_SMS_ENABLED,
    ALERT_SMS_PROVIDER,
    ALERT_SMS_TWILIO_ACCOUNT_SID,
    ALERT_SMS_TWILIO_AUTH_TOKEN,
    ALERT_SMS_TWILIO_FROM,
    ALERT_SMS_TO,
    ALERT_SMS_EMAIL_GATEWAY,
)

logger = logging.getLogger(__name__)


class AlertService:
    """Service for sending real-time alerts when large trades are captured."""

    def __init__(self):
        self.email_enabled = ALERT_EMAIL_ENABLED
        self.sms_enabled = ALERT_SMS_ENABLED

    def _get_email_recipients(self) -> List[str]:
        """
        Get list of email recipients from database, with env var fallback.
        
        Returns:
            List of email addresses
        """
        emails = []
        
        # Try database first
        try:
            with Session(engine) as session:
                recipients = session.exec(
                    select(AlertRecipient).where(
                        AlertRecipient.email.isnot(None),
                        AlertRecipient.email_enabled == True
                    )
                ).all()
                emails = [r.email for r in recipients if r.email]
        except Exception as e:
            logger.debug(f"Failed to fetch email recipients from database: {e}")
        
        # Fallback to env var if no database recipients
        if not emails and ALERT_EMAIL_TO:
            # Support comma-separated list in env var
            emails = [e.strip() for e in ALERT_EMAIL_TO.split(",") if e.strip()]
        
        return emails

    def _get_sms_recipients(self) -> List[str]:
        """
        Get list of SMS recipients (phone numbers) from database, with env var fallback.
        
        Returns:
            List of phone numbers
        """
        phones = []
        
        # Try database first
        try:
            with Session(engine) as session:
                recipients = session.exec(
                    select(AlertRecipient).where(
                        AlertRecipient.phone.isnot(None),
                        AlertRecipient.sms_enabled == True
                    )
                ).all()
                phones = [r.phone for r in recipients if r.phone]
        except Exception as e:
            logger.debug(f"Failed to fetch SMS recipients from database: {e}")
        
        # Fallback to env var if no database recipients
        if not phones and ALERT_SMS_TO:
            # Support comma-separated list in env var
            phones = [p.strip() for p in ALERT_SMS_TO.split(",") if p.strip()]
        
        return phones

    def send_trade_alert(self, order: OrderFlow) -> Dict[str, bool]:
        """
        Send alerts for a captured large trade to all configured recipients.
        
        Args:
            order: OrderFlow record that was just saved
            
        Returns:
            Dict with 'email_sent', 'sms_sent', 'email_count', 'sms_count'
        """
        results = {"email_sent": False, "sms_sent": False, "email_count": 0, "sms_count": 0}
        
        if self.email_enabled:
            try:
                email_count = self._send_email_alert(order)
                results["email_sent"] = email_count > 0
                results["email_count"] = email_count
            except Exception as e:
                logger.error("Failed to send email alert: %s", e, exc_info=True)
        
        if self.sms_enabled:
            try:
                sms_count = self._send_sms_alert(order)
                results["sms_sent"] = sms_count > 0
                results["sms_count"] = sms_count
            except Exception as e:
                logger.error("Failed to send SMS alert: %s", e, exc_info=True)
        
        return results

    def _send_email_alert(self, order: OrderFlow) -> int:
        """
        Send email alert via SMTP to all configured recipients.
        
        Returns:
            Number of emails sent successfully
        """
        if not all([ALERT_EMAIL_SMTP_HOST, ALERT_EMAIL_SMTP_USER, ALERT_EMAIL_FROM]):
            logger.warning("Email alert configuration incomplete")
            return 0
        
        recipients = self._get_email_recipients()
        if not recipients:
            logger.warning("No email recipients configured")
            return 0
        
        # Format message
        subject = f"🚨 Large Trade Alert: {order.display_ticker or order.ticker}"
        
        body = f"""
Large Trade Detected

Ticker: {order.display_ticker or order.ticker}
Instrument: {order.instrument.upper()}
Side: {order.order_side.upper() if order.order_side else 'UNKNOWN'}
Size: ${order.order_size_usd:,.2f}
Price: ${order.price:.2f}
Shares/Contracts: {order.size or 'N/A'}
Timestamp: {order.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

"""
        
        if order.instrument == "option":
            body += f"""
Option Details:
  Type: {order.option_type.upper() if order.option_type else 'N/A'}
  Strike: {f"${order.option_strike:.2f}" if order.option_strike else 'N/A'}
  Expiration: {order.option_expiration.strftime('%Y-%m-%d') if order.option_expiration else 'N/A'}
  Contracts: {order.contracts or 'N/A'}
"""
        
        body += f"""
View in dashboard: [Your dashboard URL]/order-flow

---
Bot Trader Watcher
"""
        
        # Send to all recipients
        port = ALERT_EMAIL_SMTP_PORT or 587
        use_tls = port == 587
        sent_count = 0
        
        with smtplib.SMTP(ALERT_EMAIL_SMTP_HOST, port) as server:
            if use_tls:
                server.starttls()
            if ALERT_EMAIL_SMTP_PASSWORD:
                server.login(ALERT_EMAIL_SMTP_USER, ALERT_EMAIL_SMTP_PASSWORD)
            
            # Send to each recipient
            for recipient_email in recipients:
                try:
                    msg = MIMEMultipart()
                    msg["From"] = ALERT_EMAIL_FROM
                    msg["To"] = recipient_email
                    msg["Subject"] = subject
                    msg.attach(MIMEText(body, "plain"))
                    server.send_message(msg)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send email to {recipient_email}: {e}")
        
        logger.info("Email alerts sent to %d recipients for %s trade", sent_count, order.ticker)
        return sent_count

    def _send_sms_alert(self, order: OrderFlow) -> int:
        """
        Send SMS alert via configured provider to all recipients.
        
        Returns:
            Number of SMS sent successfully
        """
        recipients = self._get_sms_recipients()
        if not recipients:
            logger.warning("No SMS recipients configured")
            return 0
        
        if ALERT_SMS_PROVIDER == "twilio":
            return self._send_sms_twilio(order, recipients)
        elif ALERT_SMS_PROVIDER == "email_gateway":
            return self._send_sms_email_gateway(order, recipients)
        else:
            logger.warning("Unknown SMS provider: %s", ALERT_SMS_PROVIDER)
            return 0

    def _send_sms_twilio(self, order: OrderFlow, recipients: List[str]) -> int:
        """
        Send SMS via Twilio API to all recipients.
        
        Returns:
            Number of SMS sent successfully
        """
        if not all([ALERT_SMS_TWILIO_ACCOUNT_SID, ALERT_SMS_TWILIO_AUTH_TOKEN, ALERT_SMS_TWILIO_FROM]):
            logger.warning("Twilio configuration incomplete")
            return 0
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{ALERT_SMS_TWILIO_ACCOUNT_SID}/Messages.json"
        
        message = (
            f"🚨 Large Trade: {order.display_ticker or order.ticker} "
            f"{order.order_side.upper() if order.order_side else ''} "
            f"${order.order_size_usd:,.0f} @ ${order.price:.2f}"
        )
        
        sent_count = 0
        for phone in recipients:
            try:
                data = {
                    "From": ALERT_SMS_TWILIO_FROM,
                    "To": phone,
                    "Body": message,
                }
                
                resp = requests.post(
                    url,
                    data=data,
                    auth=(ALERT_SMS_TWILIO_ACCOUNT_SID, ALERT_SMS_TWILIO_AUTH_TOKEN),
                    timeout=10,
                )
                resp.raise_for_status()
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send SMS to {phone}: {e}")
        
        logger.info("SMS alerts sent via Twilio to %d recipients for %s trade", sent_count, order.ticker)
        return sent_count

    def _send_sms_email_gateway(self, order: OrderFlow, recipients: List[str]) -> int:
        """
        Send SMS via email-to-SMS gateway (carrier email gateway) to all recipients.
        
        Note: This requires ALERT_SMS_EMAIL_GATEWAY to be set with a domain pattern
        (e.g., "@vtext.com" for Verizon). Each recipient phone will be formatted as
        {phone}@{domain}.
        
        Returns:
            Number of SMS sent successfully
        """
        if not all([ALERT_EMAIL_SMTP_HOST, ALERT_EMAIL_SMTP_USER, ALERT_EMAIL_FROM, ALERT_SMS_EMAIL_GATEWAY]):
            logger.warning("Email-to-SMS configuration incomplete")
            return 0
        
        # Format SMS message (shorter than email)
        message = (
            f"🚨 {order.display_ticker or order.ticker} "
            f"{order.order_side.upper() if order.order_side else ''} "
            f"${order.order_size_usd:,.0f} @ ${order.price:.2f}"
        )
        
        # Extract domain from gateway (e.g., "@vtext.com" or "1234567890@vtext.com")
        gateway_domain = ALERT_SMS_EMAIL_GATEWAY
        if "@" in gateway_domain:
            # If full email provided, extract domain
            gateway_domain = "@" + gateway_domain.split("@")[-1]
        
        # Send via SMTP
        port = ALERT_EMAIL_SMTP_PORT or 587
        use_tls = port == 587
        sent_count = 0
        
        with smtplib.SMTP(ALERT_EMAIL_SMTP_HOST, port) as server:
            if use_tls:
                server.starttls()
            if ALERT_EMAIL_SMTP_PASSWORD:
                server.login(ALERT_EMAIL_SMTP_USER, ALERT_EMAIL_SMTP_PASSWORD)
            
            # Send to each recipient
            for phone in recipients:
                try:
                    # Format phone as email (e.g., "1234567890@vtext.com")
                    # Remove any non-digit characters from phone
                    phone_clean = "".join(filter(str.isdigit, phone))
                    email_address = f"{phone_clean}{gateway_domain}"
                    
                    msg = MIMEText(message)
                    msg["From"] = ALERT_EMAIL_FROM
                    msg["To"] = email_address
                    msg["Subject"] = ""  # Some gateways ignore subject
                    server.send_message(msg)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send SMS to {phone}: {e}")
        
        logger.info("SMS alerts sent via email gateway to %d recipients for %s trade", sent_count, order.ticker)
        return sent_count


# Global alert service instance
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """Get or create global alert service instance."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service

