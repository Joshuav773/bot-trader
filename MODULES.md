# Module Walkthrough & Logic Streamlining

This document walks through each module to understand and streamline the logic.

## 1. Order Flow Tracking Module

**Purpose**: Track large orders (>= $500k) and analyze price impact for prediction.

### Files
- `order_flow/aggregator.py` - Filters trades >= $500k
- `order_flow/price_tracker.py` - Captures price snapshots at intervals
- `order_flow/streamer.py` - Real-time streamer (placeholder)
- `api/models.py` - `OrderFlow` and `PriceSnapshot` tables
- `api/routers/orderflow.py` - API endpoints

### Current Logic Flow
1. **Aggregator**: Receives trade data → calculates USD value → filters if >= $500k → saves to DB
2. **Price Tracker**: After order saved → fetches price at 1m, 5m, 15m, 1h, 1d → calculates % change → saves snapshots
3. **API**: Queries DB for orders, calculates statistics

### Questions to Streamline
- Should we use WebSocket streaming or polling? (Currently placeholder)
- How do we handle S&P 500 ticker list? (Hardcoded sample, should be dynamic)
- Should price snapshots be captured automatically or on-demand?
- How to handle missing data when capturing snapshots?

---

## 2. Confluence Strategy Module

**Purpose**: Multi-confirmation strategy requiring trend + momentum + volume + candlestick + news.

### Files
- `backtester/strategies/confluence.py` - Strategy logic
- `api/routers/confluence.py` - Backtest/optimize endpoints
- `analysis_engine/candlestick_patterns.py` - Pattern detection

### Current Logic Flow
1. **Confirmation Counting**: Checks 5 factors:
   - Trend: Fast MA > Slow MA
   - Momentum: RSI in bullish range
   - Volume: Above threshold
   - Candlestick: Bullish pattern detected
   - News: Positive sentiment > threshold
2. **Entry**: If confirmations >= min_confirmations AND trend bullish → BUY
3. **Exit**: If confirmations drop OR trend reverses → SELL

### Questions to Streamline
- Should all 5 confirmations be required, or just min_confirmations?
- News sentiment: How to handle when news API fails? (Currently returns None, doesn't count)
- Candlestick patterns: Are we detecting all relevant patterns? (Currently hammer + engulfing)
- Should we weight confirmations differently? (e.g., news might be less reliable than trend)

---

## 3. Forex Module

**Purpose**: Forex-specific confluence strategy optimized for major pairs.

### Files
- `backtester/strategies/forex_confluence.py` - Forex strategy (extends ConfluenceStrategy)
- `ml_models/forex_learning_agent.py` - Learning agent
- `api/routers/forex.py` - Forex endpoints

### Current Logic Flow
1. **Forex Strategy**: Same as confluence but:
   - Adjusted RSI thresholds (25/75 vs 30/70)
   - Lower volume threshold (1.15 vs 1.2)
   - Lower news threshold (0.05 vs 0.1)
   - Forex-specific news (analyzes base + quote currency)
2. **Learning Agent**: Grid searches parameters across major pairs, finds aggregate best settings

### Questions to Streamline
- Forex news: How to combine base + quote currency sentiment? (Currently averages, but logic might need refinement)
- Should we have different confirmation requirements for different pairs?
- Learning agent: Should we optimize per-pair or use aggregate? (Currently does both)
- Commission: 0.0001 (0.01%) is typical, but should be configurable

---

## 4. News Sentiment Module

**Purpose**: Fetch news and analyze sentiment using FinBERT for trading signals.

### Files
- `data_ingestion/news_client.py` - News fetching + sentiment analysis
- `analysis_engine/sentiment_analyzer.py` - FinBERT wrapper
- `api/routers/news.py` - News endpoints

### Current Logic Flow
1. **Fetch News**: Polygon API → filter by date → combine title + description
2. **Analyze**: FinBERT → sentiment probabilities (positive/negative/neutral)
3. **Aggregate**: Average sentiment scores, determine bullish/bearish/neutral

### Questions to Streamline
- News API rate limits: How to handle? (Currently no throttling)
- Sentiment scoring: Current formula is `positive - negative`. Is this correct?
- Forex pairs: How to handle sentiment for pairs? (Currently analyzes base currency, then subtracts quote)
- Caching: Strategy caches per date, but should we cache more aggressively?

---

## 5. Candlestick Patterns Module

**Purpose**: Detect bullish/bearish candlestick patterns.

### Files
- `analysis_engine/candlestick_patterns.py` - Pattern detection functions

### Current Patterns
- Hammer (bullish reversal)
- Engulfing (bullish/bearish)
- Doji (indecision)
- Shooting Star (bearish reversal)

### Questions to Streamline
- Are we detecting patterns correctly? (Logic seems sound, but should verify)
- Should we add more patterns? (Morning star, evening star, three white soldiers, etc.)
- Pattern strength: Should we weight strong patterns higher than weak ones?

---

## Next Steps

1. **Review each module** one by one
2. **Identify logic issues** or improvements
3. **Streamline** based on your feedback
4. **Test** each module independently

Which module should we start with?

