# Plan: Scan Every Order and Detect Large Ones

## Current State

### What We Have
✅ **Streaming Bot** (`schwab_streamer.py`)
- Streams Level 1 quotes for 100 S&P 500 stocks
- Detects large orders (>= $50k) via bid/ask size changes
- Detects large trades (>= $50k) via volume changes
- Saves to database (`order_flow` table)
- Sends email notifications

✅ **Detection Methods**
- `order_tracker.py`: Monitors bid/ask size changes (detects when orders are placed)
- `trade_tracker.py`: Monitors volume changes (detects executed trades)

### Current Limitations

#### 1. **API Limitations**
❌ **Schwab REST API does NOT provide:**
- Individual order executions (historical or real-time)
- Order book depth data (Level 2) via REST
- Market-wide order flow data

✅ **Schwab Streaming API provides:**
- Level 1 quotes: bid, ask, last price, volume, bid size, ask size
- Real-time updates (not historical)
- Limited to symbols you subscribe to

#### 2. **Detection Limitations**
❌ **Current detection methods:**
- Only detects orders when bid/ask size changes significantly
- May miss orders that execute immediately (no size change)
- May miss hidden/iceberg orders
- Cannot see order book depth (how many orders at each price level)

#### 3. **Coverage Limitations**
❌ **Currently scanning:**
- Only 100 S&P 500 stocks (out of 500+)
- Only stocks (not options)
- Only during market hours

## What We CAN Do (Improvements)

### 1. **Expand Symbol Coverage**
**Goal:** Scan ALL S&P 500 stocks (or more)

**Implementation:**
- Increase `SP500_SYMBOLS` list to all 500+ stocks
- Handle subscription limits (Schwab may have limits)
- Prioritize high-volume stocks first

**Limitation:** Schwab may limit concurrent subscriptions

### 2. **Improve Order Detection**
**Goal:** Catch more large orders

**Current Method:**
- Monitor bid/ask size changes
- Threshold: $50k

**Improvements:**
- **Lower threshold** (if needed): Currently $50k, can go lower
- **Volume spike detection**: Detect sudden volume increases
- **Price movement analysis**: Large price moves often indicate large orders
- **Combined signals**: Use multiple indicators together
- **Time-based filtering**: Ignore small changes, focus on significant ones

**New Detection Methods:**
```python
# Method 1: Volume spike detection
if volume_delta > threshold and volume_delta > last_volume * 0.1:
    # Large order executed

# Method 2: Price impact analysis
if abs(price_change) > threshold and volume_delta > threshold:
    # Large order with price impact

# Method 3: Bid/Ask imbalance
if bid_size >> ask_size or ask_size >> bid_size:
    # Large order on one side
```

### 3. **Add Options Scanning**
**Goal:** Detect large options orders (PUT/CALL)

**Implementation:**
- Subscribe to options symbols (format: `AAPL_240119C150`)
- Use same detection logic
- Parse options data (strike, expiration, type)

**Limitation:** Need to know which options to scan (can't scan all)

### 4. **Level 2 Data (If Available)**
**Goal:** See order book depth

**Check:** Does Schwab streaming API support Level 2?
- If yes: Subscribe to Level 2 data
- See actual order book (bids/asks at each price level)
- Detect large orders before they execute

**Implementation:**
```python
# If Level 2 available
await stream_client.level_two_equity_subs(symbols=[symbol])
# Process order book data
```

### 5. **Real-Time Processing Improvements**
**Goal:** Process more data faster

**Current:**
- Processes quotes as they arrive
- Checks each symbol individually

**Improvements:**
- **Batch processing**: Process multiple symbols together
- **Parallel processing**: Use async/await more efficiently
- **Deduplication**: Avoid detecting same order multiple times
- **Rate limiting**: Handle API rate limits gracefully

### 6. **Better Filtering**
**Goal:** Reduce false positives, catch more real orders

**Improvements:**
- **Time windows**: Only alert if order persists for X seconds
- **Confirmation**: Require multiple signals before alerting
- **Size validation**: Verify order size makes sense
- **Price validation**: Check if price is reasonable

## Implementation Plan

### Phase 1: Improve Detection (Immediate)
1. ✅ Lower threshold to $50k (already done)
2. ⬜ Add volume spike detection
3. ⬜ Add price impact analysis
4. ⬜ Combine multiple signals
5. ⬜ Add deduplication logic

### Phase 2: Expand Coverage
1. ⬜ Add all S&P 500 symbols (500+ stocks)
2. ⬜ Test subscription limits
3. ⬜ Prioritize high-volume stocks
4. ⬜ Add error handling for subscription failures

### Phase 3: Options Support
1. ⬜ Research options symbol format
2. ⬜ Add options subscription
3. ⬜ Parse options data (strike, expiration, type)
4. ⬜ Test with popular options

### Phase 4: Advanced Features
1. ⬜ Check for Level 2 data availability
2. ⬜ Implement Level 2 if available
3. ⬜ Add order book analysis
4. ⬜ Improve filtering and validation

## Technical Constraints

### Schwab API Limits
- **Streaming connections**: May have limits on concurrent subscriptions
- **Rate limits**: May throttle if too many requests
- **Data fields**: Limited to what Level 1 provides

### Detection Accuracy
- **False positives**: Small size changes may not be real orders
- **Missed orders**: Orders that execute instantly may not show size changes
- **Hidden orders**: Iceberg orders may not be visible

### Performance
- **Processing speed**: Need to process quotes fast enough
- **Database writes**: May bottleneck with many orders
- **Email sending**: May be rate-limited

## Recommendations

### Immediate Actions (This Week)
1. **Improve detection algorithm** - Add volume spike + price impact
2. **Add deduplication** - Avoid duplicate alerts
3. **Expand to all S&P 500** - Test with full list
4. **Better logging** - Track detection accuracy

### Short Term (This Month)
1. **Options support** - Add options scanning
2. **Level 2 research** - Check if available
3. **Performance optimization** - Speed up processing
4. **Monitoring dashboard** - Track detection stats

### Long Term (Next Quarter)
1. **Machine learning** - Improve detection accuracy
2. **Multi-exchange** - If needed, add other data sources
3. **Advanced analytics** - Order flow analysis
4. **Real-time dashboard** - Web interface for monitoring

## Questions to Answer

1. **Does Schwab support Level 2 streaming?** (Need to check API docs)
2. **What are the subscription limits?** (Test with 500 symbols)
3. **Can we get options data?** (Check symbol format)
4. **What's the best threshold?** (Test different values)
5. **How to handle false positives?** (Add confirmation logic)

## Next Steps

1. **Research Level 2 availability** - Check Schwab API documentation
2. **Test with more symbols** - Expand to all S&P 500
3. **Improve detection** - Add new detection methods
4. **Add options** - If possible
5. **Monitor and optimize** - Track what works best


