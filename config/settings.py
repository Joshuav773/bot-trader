import os
from dotenv import load_dotenv

load_dotenv()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

MASTER_API_TOKEN = os.getenv("MASTER_API_TOKEN")
# CORS origins - provide sensible defaults if not set
# Handle errors gracefully to prevent app crashes
try:
    _cors_origins_str = os.getenv("CORS_ALLOW_ORIGINS", "")
    if not _cors_origins_str:
        # Default to localhost + common Vercel pattern if not set
        _cors_origins_str = "http://localhost:3000,http://127.0.0.1:3000,https://bot-trader-xi.vercel.app"
        print("⚠ CORS_ALLOW_ORIGINS not set, using defaults")
    
    CORS_ALLOW_ORIGINS = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]
    # Ensure we always have at least localhost for development
    if not CORS_ALLOW_ORIGINS:
        CORS_ALLOW_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "https://bot-trader-xi.vercel.app"]
    
    print(f"✓ CORS origins configured: {len(CORS_ALLOW_ORIGINS)} origin(s)")
    print(f"   Origins: {CORS_ALLOW_ORIGINS}")
except Exception as e:
    print(f"⚠ Warning: Error parsing CORS_ALLOW_ORIGINS: {e}")
    print("   Using default origins")
    CORS_ALLOW_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "https://bot-trader-xi.vercel.app"]

DATABASE_URL = os.getenv("DATABASE_URL")  # e.g., postgres://user:pass@host/db
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "60"))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not POLYGON_API_KEY:
    print("❌ POLYGON_API_KEY not set in environment")
else:
    print("✓ POLYGON_API_KEY loaded from environment")

# Polygon.io API Data Limits (days of historical data available per timeframe)
# These can be adjusted based on your Polygon.io subscription tier
# Free tier limits: 5m=30d, 15m=60d, 30m=90d, 1h=2y, 4h=2y, 1d=unlimited
# Paid tiers may have extended limits
POLYGON_DATA_LIMITS = {
    "5m": int(os.getenv("POLYGON_LIMIT_5M", "30")),  # 5-minute: 30 days (free tier)
    "15m": int(os.getenv("POLYGON_LIMIT_15M", "60")),  # 15-minute: 60 days (free tier)
    "30m": int(os.getenv("POLYGON_LIMIT_30M", "90")),  # 30-minute: 90 days (free tier)
    "1h": int(os.getenv("POLYGON_LIMIT_1H", "730")),  # 1-hour: ~2 years (730 days)
    "4h": int(os.getenv("POLYGON_LIMIT_4H", "730")),  # 4-hour: ~2 years (730 days)
    "1d": int(os.getenv("POLYGON_LIMIT_1D", "3650")),  # Daily: 10 years (can be extended)
}
