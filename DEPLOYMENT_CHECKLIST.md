# Streamer Deployment Checklist

## ✅ Ready for Deployment

The streamer is **production-ready** with all core features implemented.

## Database Storage

**YES - All orders are being stored to the database:**

1. **Large Orders (from Level 1 quotes)**
   - Method: `save_large_order()`
   - Table: `order_flow`
   - Source: `'streamer'`
   - Threshold: >= $50,000

2. **Large Orders (from Order Book - Level 2)**
   - Method: `save_large_order()` or `save_all_order()`
   - Table: `order_flow`
   - Source: `'order_book'`
   - Threshold: >= $50,000 (or all if `SCAN_ALL_ORDERS=true`)

3. **Large Trades**
   - Method: `save_large_trade()`
   - Table: `order_flow`
   - Source: `'streamer'`
   - Threshold: >= $50,000

## What Gets Saved

Each order/trade record includes:
- `ticker` - Symbol (e.g., NVDA, AAPL)
- `order_type` - Type of order (BUY_ORDER, SELL_ORDER, LARGE_TRADE, etc.)
- `order_size_usd` - Order value in USD
- `price` - Execution/order price
- `timestamp` - When it was detected
- `source` - Where it came from ('streamer' or 'order_book')
- `raw_data` - Full JSON data (detection method, exchange, etc.)
- `instrument` - 'equity' or 'option'
- `order_side` - 'BUY' or 'SELL'

## Pre-Deployment Checklist

### 1. Environment Variables

Ensure these are set in your `.env` or production environment:

```bash
# Schwab API
SCHWAB_APP_KEY=your_app_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=http://127.0.0.1:8080
SCHWAB_TOKEN_JSON={"access_token":"...","refresh_token":"..."}  # For production

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Email Notifications
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=your_app_password

# Optional: Scan all orders (default: false)
SCAN_ALL_ORDERS=false  # Set to true to save ALL orders, not just large ones
```

### 2. Database Setup

Ensure `order_flow` table exists with these columns:
- `id` (primary key)
- `ticker` (varchar)
- `order_type` (varchar)
- `order_size_usd` (numeric)
- `price` (numeric)
- `timestamp` (timestamp)
- `source` (varchar)
- `raw_data` (jsonb or text)
- `display_ticker` (varchar)
- `instrument` (varchar)
- `order_side` (varchar)

### 3. Token Management

**For Production:**
- Set `SCHWAB_TOKEN_JSON` environment variable with valid token
- Token should be refreshed periodically (Schwab tokens expire)

**For Local Development:**
- Run `python3 schwab_streamer.py` once to generate `token.json`
- Token will be auto-refreshed when needed

### 4. Testing

Before deploying, test:
- ✅ Database connection
- ✅ Order detection (run test script)
- ✅ Email notifications
- ✅ Reconnection logic
- ✅ Order book subscriptions

## Deployment Steps

### Option 1: GCP VM (Recommended)

1. **Deploy to VM:**
   ```bash
   # Follow scripts/gcp_deploy.md
   ```

2. **Run as systemd service:**
   ```bash
   sudo systemctl start bot-trader-streamer
   sudo systemctl enable bot-trader-streamer
   ```

3. **Monitor logs:**
   ```bash
   sudo journalctl -u bot-trader-streamer -f
   ```

### Option 2: Screen/Tmux

```bash
# Start in screen
screen -S streamer
python3 schwab_streamer.py

# Detach: Ctrl+A, then D
# Reattach: screen -r streamer
```

### Option 3: Nohup

```bash
nohup python3 schwab_streamer.py > streamer.log 2>&1 &
```

## Monitoring

### Check if Running

```bash
ps aux | grep schwab_streamer
```

### Check Database

```bash
python3 check_orders_db.py
python3 check_orders_db.py --recent  # Last hour
```

### Check Logs

```bash
tail -f streamer.log  # If using nohup
journalctl -u bot-trader-streamer -f  # If using systemd
```

## Current Status

✅ **READY FOR DEPLOYMENT**

- All features implemented
- Database saving working
- Email notifications working
- Error handling robust
- Reconnection logic implemented
- Tested with real data

## Next Steps

1. ✅ Set environment variables
2. ✅ Verify database connection
3. ✅ Test locally first
4. ✅ Deploy to production
5. ✅ Monitor logs and database

## Notes

- **Order Volume**: If `SCAN_ALL_ORDERS=true`, expect thousands of orders per minute. Ensure database can handle the load.
- **Token Refresh**: Schwab tokens expire. The streamer handles refresh automatically, but ensure `SCHWAB_TOKEN_JSON` is kept up to date.
- **Market Hours**: Streamer works best during market hours (9:30 AM - 4:00 PM ET). Outside hours, data may be limited.

