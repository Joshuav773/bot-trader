"""
Application settings and configuration.

All configuration is loaded from environment variables via .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Schwab Streaming API Configuration
# ============================================================================
SCHWAB_APP_KEY = os.getenv("SCHWAB_APP_KEY")
SCHWAB_APP_SECRET = os.getenv("SCHWAB_APP_SECRET")
SCHWAB_CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "http://localhost")

if SCHWAB_APP_KEY and SCHWAB_APP_SECRET:
    print("✓ Schwab Streaming API credentials loaded")
else:
    print("⚠ SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set for streaming")

# ============================================================================
# Database Configuration
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("⚠ DATABASE_URL not set - using SQLite fallback")
    DATABASE_URL = "sqlite:///./app.db"

# ============================================================================
# Authentication & Security
# ============================================================================
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "60"))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

MASTER_API_TOKEN = os.getenv("MASTER_API_TOKEN")

# ============================================================================
# CORS Configuration
# ============================================================================
try:
    _cors_origins_str = os.getenv("CORS_ALLOW_ORIGINS", "")
    if not _cors_origins_str:
        _cors_origins_str = "http://localhost:3000,http://127.0.0.1:3000"
        print("⚠ CORS_ALLOW_ORIGINS not set, using defaults")
    
    CORS_ALLOW_ORIGINS = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]
    if not CORS_ALLOW_ORIGINS:
        CORS_ALLOW_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    print(f"✓ CORS origins configured: {len(CORS_ALLOW_ORIGINS)} origin(s)")
except Exception as e:
    print(f"⚠ Warning: Error parsing CORS_ALLOW_ORIGINS: {e}")
    CORS_ALLOW_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

# ============================================================================
# Alert Configuration
# ============================================================================
def _parse_bool(value: str | None, default: bool) -> bool:
    """Parse boolean from environment variable."""
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# Email Alerts
ALERT_EMAIL_ENABLED = _parse_bool(os.getenv("ALERT_EMAIL_ENABLED"), False)
ALERT_EMAIL_SMTP_HOST = os.getenv("ALERT_EMAIL_SMTP_HOST")
ALERT_EMAIL_SMTP_PORT = int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587"))
ALERT_EMAIL_SMTP_USER = os.getenv("ALERT_EMAIL_SMTP_USER")
ALERT_EMAIL_SMTP_PASSWORD = os.getenv("ALERT_EMAIL_SMTP_PASSWORD")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")

# SMS Alerts
ALERT_SMS_ENABLED = _parse_bool(os.getenv("ALERT_SMS_ENABLED"), False)
ALERT_SMS_PROVIDER = os.getenv("ALERT_SMS_PROVIDER", "twilio").lower()

# Twilio SMS
ALERT_SMS_TWILIO_ACCOUNT_SID = os.getenv("ALERT_SMS_TWILIO_ACCOUNT_SID")
ALERT_SMS_TWILIO_AUTH_TOKEN = os.getenv("ALERT_SMS_TWILIO_AUTH_TOKEN")
ALERT_SMS_TWILIO_FROM = os.getenv("ALERT_SMS_TWILIO_FROM")
ALERT_SMS_TO = os.getenv("ALERT_SMS_TO")

# Email-to-SMS Gateway (free alternative)
ALERT_SMS_EMAIL_GATEWAY = os.getenv("ALERT_SMS_EMAIL_GATEWAY")

# ============================================================================
# Streamer Configuration
# ============================================================================
# Minimum order size to trigger whale alert (in USD)
MIN_ORDER_SIZE_USD = float(os.getenv("MIN_ORDER_SIZE_USD", "500000"))

# Custom watchlist (optional - defaults to S&P 500)
ORDER_FLOW_TICKERS = os.getenv("ORDER_FLOW_TICKERS")  # Comma-separated list
