# Backtest Results Explained 🎓

## What is Backtesting?

**Backtesting** = Testing a trading strategy on historical data to see how it would have performed.

Think of it like: "If I had used this strategy in the past, how much money would I have made/lost?"

---

## How It Works: Step-by-Step

### 1. **Get Historical Data**
```python
# We fetch real price data from Polygon.io
data = get_daily_bars("AAPL", "2019-01-01", "2024-10-30")
# Returns: [Date, Open, High, Low, Close, Volume] for each day
```

### 2. **Create a Virtual Trading Account**
```python
cash = 10000.0  # Start with $10,000
commission = 0.001  # Pay 0.1% commission per trade
```

### 3. **Run the Strategy Day-by-Day**
The backtester simulates going through each day in the past:
- **Day 1**: Check strategy rules → Buy? Sell? Hold?
- **Day 2**: Check strategy rules → Buy? Sell? Hold?
- ... continues for all days ...

### 4. **Calculate Final Results**
- How much money did we start with?
- How much money do we have now?
- What's the profit/loss?

---

## SMA Crossover Strategy Explained

### What are Moving Averages?

**SMA (Simple Moving Average)** = Average price over X days

Example:
- Fast MA (10 days) = Average of last 10 days' closing prices
- Slow MA (50 days) = Average of last 50 days' closing prices

### The Strategy Logic

```
IF Fast MA crosses ABOVE Slow MA:
    → This means price is going UP (bullish)
    → BUY signal

IF Fast MA crosses BELOW Slow MA:
    → This means price is going DOWN (bearish)
    → SELL signal (close position)
```

**Visual Example:**
```
Price: $100 → $110 → $120 → $115 → $105
Fast MA (10): $108 → $112 → $118 → $115 → $110
Slow MA (50): $105 → $107 → $109 → $110 → $109

Day 3: Fast ($118) > Slow ($109) → BUY
Day 5: Fast ($110) < Slow ($109) → SELL
```

---

## Code Walkthrough

### Step 1: Strategy Class (`sma_crossover.py`)

```python
class SmaCross(bt.Strategy):
    params = (
        ("fast_length", 10),  # 10-day moving average
        ("slow_length", 50), # 50-day moving average
    )
    
    def __init__(self):
        # Calculate moving averages
        self.fast_ma = SimpleMovingAverage(close_prices, period=10)
        self.slow_ma = SimpleMovingAverage(close_prices, period=50)
        # Detect when they cross
        self.crossover = CrossOver(self.fast_ma, self.slow_ma)
    
    def next(self):
        # This runs for EACH day in the backtest
        if not self.position:  # We don't own any stock
            if self.crossover > 0:  # Fast MA just crossed above Slow MA
                self.buy()  # Buy the stock
        else:  # We own stock
            if self.crossover < 0:  # Fast MA just crossed below Slow MA
                self.close()  # Sell the stock
```

**Python Learning:**
- `__init__` = Constructor, runs once when strategy starts
- `next()` = Runs for every day (like a loop)
- `self.position` = How many shares we own (0 = no position)
- `self.buy()` = Backtrader function to buy at current price
- `self.close()` = Backtrader function to sell everything

### Step 2: Backtest Engine (`engine.py`)

```python
def run_backtest(strategy_class, data, cash=10000.0, commission=0.001):
    # 1. Create a "brain" (cerebro) to run the backtest
    cerebro = bt.Cerebro()
    
    # 2. Add our strategy
    cerebro.addstrategy(strategy_class)
    
    # 3. Add historical data
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    
    # 4. Set starting cash
    cerebro.broker.setcash(cash)  # $10,000
    
    # 5. Set commission (trading fees)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% per trade
    
    # 6. Record starting value
    start_value = cerebro.broker.getvalue()  # $10,000
    
    # 7. RUN THE BACKTEST (goes through every day)
    cerebro.run()
    
    # 8. Get final value
    end_value = cerebro.broker.getvalue()
    
    # 9. Calculate results
    return {
        "start_portfolio_value": start_value,  # $10,000
        "end_portfolio_value": end_value,      # e.g., $12,500
        "pnl": end_value - start_value         # $2,500 profit
    }
```

**Python Learning:**
- `cerebro` = Backtrader's "brain" that simulates trading
- `broker` = The virtual trading account (handles buy/sell orders)
- `.run()` = Starts the simulation, goes through all days

### Step 3: API Endpoint (`backtest.py`)

```python
@router.post("/sma-crossover")
def backtest_sma_crossover(req: BacktestRequest):
    # 1. Get historical data from Polygon.io
    data = _client().get_daily_bars(req.ticker, req.start_date, req.end_date)
    
    # 2. Create strategy with custom parameters
    class ParamSmaCross(SmaCross):
        params = (
            ("fast_length", req.fast_length),  # User's fast MA (e.g., 10)
            ("slow_length", req.slow_length),  # User's slow MA (e.g., 50)
        )
    
    # 3. Run the backtest
    results = run_backtest(ParamSmaCross, data, cash=req.cash)
    
    # 4. Return results to frontend
    return results
```

**Python Learning:**
- `@router.post` = FastAPI decorator (creates API endpoint)
- `req: BacktestRequest` = Type hint (tells Python what data to expect)
- `class ParamSmaCross(SmaCross)` = Inherits from SmaCross, changes parameters

---

## Understanding the Results

### What You See in the UI:

```json
{
  "start_portfolio_value": 10000.00,
  "end_portfolio_value": 12500.00,
  "pnl": 2500.00,
  "pnl_percentage": 25.00
}
```

### What Each Field Means:

1. **`start_portfolio_value`** ($10,000)
   - How much money you started with
   - This is your initial cash

2. **`end_portfolio_value`** ($12,500)
   - How much money you have at the end
   - Includes: Cash + Value of any stocks you own
   - If you have stocks, it uses the final day's closing price

3. **`pnl`** ($2,500)
   - **P&L = Profit and Loss**
   - `pnl = end_value - start_value`
   - Positive = Profit ✅
   - Negative = Loss ❌

4. **`pnl_percentage`** (25%)
   - Percentage return
   - `pnl_percentage = (pnl / start_value) * 100`
   - 25% = You made 25% profit

---

## Example Walkthrough

Let's say you backtest AAPL from Jan 1, 2020 to Dec 31, 2023:

### Day-by-Day Simulation:

**Jan 1, 2020:**
- Cash: $10,000
- AAPL Price: $75
- Fast MA (10): $74
- Slow MA (50): $73
- No position yet

**Jan 15, 2020:**
- AAPL Price: $78
- Fast MA (10): $76
- Slow MA (50): $74
- **Fast crosses above Slow → BUY SIGNAL**
- Buy 133 shares at $78 = $10,374 (minus commission)
- Cash left: ~$626

**March 20, 2020:**
- AAPL Price: $65
- Fast MA (10): $67
- Slow MA (50): $69
- **Fast crosses below Slow → SELL SIGNAL**
- Sell 133 shares at $65 = $8,645
- Total cash: ~$9,271
- **Loss so far: -$729**

**June 1, 2020:**
- AAPL Price: $80
- Fast MA (10): $79
- Slow MA (50): $77
- **Fast crosses above Slow → BUY SIGNAL**
- Buy 115 shares at $80 = $9,200
- Cash left: ~$71

... continues for all days ...

**Dec 31, 2023:**
- AAPL Price: $185
- We own: 115 shares
- Stock value: 115 × $185 = $21,275
- Cash: $71
- **Total portfolio: $21,346**
- **Profit: $11,346 (113% return!)**

---

## What Makes a Good Backtest?

✅ **Good Results:**
- Positive PnL
- High percentage return
- Consistent performance

❌ **Warning Signs:**
- Negative PnL (strategy loses money)
- Very few trades (strategy might be too conservative)
- Too many trades (high commission costs)

---

## Important Notes

1. **Past performance ≠ Future results**
   - Just because it worked in the past doesn't mean it will work tomorrow
   - Markets change!

2. **Commission matters**
   - Each trade costs money (0.1% in our case)
   - Too many trades = lots of fees

3. **Data quality matters**
   - We need accurate historical prices
   - Gaps in data can skew results

4. **Slippage not included**
   - In real trading, you might not get the exact price you want
   - Backtests assume perfect execution

---

## Next Steps

Want to learn more?
- Try different fast/slow MA combinations
- Test on different stocks
- Compare strategies (SMA vs Confluence)
- Add more metrics (Sharpe ratio, max drawdown, etc.)

