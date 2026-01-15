# Order Scanning Guide - Scan Every Order

## Overview

Your bot **already has Level 2 order book functionality** that can scan **every single order** for each symbol you subscribe to. This is the same data that feeds Think or Swim.

## What You Have Now

### ✅ Already Implemented

1. **Level 2 Order Book Subscriptions**
   - NASDAQ order book
   - NYSE order book  
   - Options order book

2. **Order Scanning Logic**
   - Scans ALL bids (buy orders) at each price level
   - Scans ALL asks (sell orders) at each price level
   - Processes every order in the order book snapshot

3. **Database Saving**
   - `save_all_order()` method saves every order
   - `save_large_order()` method saves only large orders (>= $50k)

4. **Configuration**
   - `SCAN_ALL_ORDERS` environment variable controls behavior

## How to Enable Scanning Every Order

### Step 1: Set Environment Variable

Add to your `.env` file:

```bash
SCAN_ALL_ORDERS=true
```

### Step 2: Verify Order Book Subscriptions

The bot automatically subscribes to order books when it starts:

```python
# In schwab_streamer.py (lines 658-670)
await self.stream_client.nasdaq_book_subs(symbols=batch)
# or
await self.stream_client.nyse_book_subs(symbols=batch)
```

### Step 3: Monitor the Logs

When `SCAN_ALL_ORDERS=true`, you'll see:
```
🔍 Mode: Scanning ALL orders from order book (every order will be saved)
📊 Order book scan: AAPL | Scanned: 150 orders | Saved: 150 orders | Exchange: NASDAQ
```

## How It Works

### Order Book Data Flow

1. **Subscription**: Bot subscribes to Level 2 order book for each symbol
2. **Data Reception**: Order book snapshots arrive via WebSocket
3. **Processing**: `process_order_book()` parses the message
4. **Scanning**: `scan_order_book()` iterates through ALL bids and asks
5. **Saving**: Each order is saved to database (when `SCAN_ALL_ORDERS=true`)

### Order Book Structure

Each order book snapshot contains:
- **Bids**: List of buy orders `[{'price': X, 'size': Y}, ...]`
- **Asks**: List of sell orders `[{'price': X, 'size': Y}, ...]`
- **Book Time**: Timestamp of the snapshot
- **Exchange**: NASDAQ, NYSE, or OPTIONS

### What Gets Saved

When `SCAN_ALL_ORDERS=true`, **EVERY order** is saved:
- Small orders (< $50k)
- Medium orders ($50k - $200k)
- Large orders (>= $200k)

Each order record includes:
- Symbol
- Order side (BUY/SELL)
- Price
- Size (shares/contracts)
- Order value (USD)
- Exchange
- Timestamp
- Detection method: `ORDER_BOOK_BID` or `ORDER_BOOK_ASK`

## Current Limitations

### 1. **Order Book Availability**
- Not all symbols may have Level 2 data available
- Some symbols may only have Level 1 (top bid/ask)
- Options order book may have limited coverage

### 2. **Data Volume**
- Scanning ALL orders generates **massive** amounts of data
- Database can fill up quickly (thousands of orders per minute)
- Consider database indexing and cleanup strategies

### 3. **Subscription Limits**
- Schwab API may have limits on:
  - Number of symbols you can subscribe to simultaneously
  - Rate of order book updates
  - WebSocket connection stability

### 4. **Order Book Updates**
- Order book snapshots arrive periodically (not every order change)
- You see snapshots, not individual order additions/removals
- Real-time order-by-order tracking requires Level 2 streaming (if available)

## Recommendations

### For Production Use

1. **Start with Large Orders Only**
   ```bash
   SCAN_ALL_ORDERS=false  # Default
   ```
   This saves only orders >= $50k

2. **Enable All Orders for Specific Symbols**
   - Modify code to scan all orders for specific high-value symbols
   - Use `SCAN_ALL_ORDERS=true` only when needed

3. **Database Optimization**
   - Add indexes on `ticker`, `timestamp`, `order_size_usd`
   - Implement data retention policies (delete old orders)
   - Consider partitioning by date

4. **Monitoring**
   - Monitor database size
   - Track order scanning rate
   - Set up alerts for database issues

## Testing

### Test Order Book Subscription

1. Run the bot:
   ```bash
   python3 schwab_streamer.py
   ```

2. Check logs for:
   ```
   ✅ Subscribed Level 1 + Order Book for batch 1 (100 symbols)
   ```

3. Look for order book messages:
   ```
   📊 Order book scan: AAPL | Scanned: 150 orders | Saved: 150 orders
   ```

### Verify Database

Check that orders are being saved:
```sql
SELECT COUNT(*) FROM order_flow WHERE source = 'order_book';
SELECT * FROM order_flow WHERE source = 'order_book' ORDER BY timestamp DESC LIMIT 10;
```

## Troubleshooting

### No Order Book Data

**Problem**: Logs show Level 1 subscriptions but no order book scans

**Solutions**:
1. Check if symbol is NASDAQ or NYSE (order book may not be available for all)
2. Verify API permissions include Level 2 data
3. Check if order book subscription succeeded (look for warnings)

### Too Much Data

**Problem**: Database filling up too quickly

**Solutions**:
1. Set `SCAN_ALL_ORDERS=false` to save only large orders
2. Reduce number of symbols subscribed
3. Implement data retention/cleanup

### Missing Orders

**Problem**: Not seeing all orders you expect

**Solutions**:
1. Order book shows orders at different price levels, not all market orders
2. Some orders may execute before appearing in book
3. Level 2 shows visible orders, not hidden/iceberg orders

## Next Steps

1. ✅ **Enable scanning**: Set `SCAN_ALL_ORDERS=true` in `.env`
2. ✅ **Test with small symbol set**: Start with 10-20 symbols
3. ✅ **Monitor database**: Check order volume and database size
4. ✅ **Optimize**: Add indexes, implement retention policies
5. ✅ **Scale up**: Gradually increase symbol count

## Summary

**You already have everything you need!** Just set `SCAN_ALL_ORDERS=true` and the bot will scan and save every order from the order book for each subscribed symbol.

The order book data is the same Level 2 data that Think or Swim uses - you're getting the full depth of market orders at each price level.

