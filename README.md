# Bot Trader

FastAPI-based trading SaaS platform for analysis, backtesting, ML training, and real-time order flow tracking.

## Features

### Core Functionality
- **JWT Authentication**: Single admin account with secure login
- **Technical Analysis**: SMA, RSI, candlestick patterns (hammer, engulfing, doji, shooting star)
- **Backtesting**: SMA crossover and advanced confluence strategies
- **Machine Learning**: LSTM price prediction with training/prediction endpoints
- **News Sentiment**: FinBERT-powered sentiment analysis for trading signals

### Advanced Features

#### 1. Order Flow Tracking (Feature 1)
- **Real-time large order detection**: Tracks orders >= $500k for S&P 500 tickers
- **Price impact analysis**: Captures price movements at 1m, 5m, 15m, 1h, 1d intervals after large orders
- **Database**: Stores order flow and price snapshots in Postgres
- **Endpoints**: 
  - `GET /order-flow/large-orders` - Get recent large orders
  - `GET /order-flow/price-impact/{order_id}` - View price impact for specific order
  - `GET /order-flow/price-impact-stats` - Aggregate statistics
- **UI**: `/orderflow` page with real-time feed and impact analysis

#### 2. Confluence Strategy (Feature 2)
- **Multi-confirmation strategy**: Requires 3-5 confirmations before entry:
  1. **Trend**: SMA crossover (fast > slow)
  2. **Momentum**: RSI in bullish range
  3. **Volume**: Volume above threshold
  4. **Candlestick**: Bullish patterns (hammer, engulfing)
  5. **News Sentiment**: Positive news sentiment (FinBERT)
- **Endpoints**:
  - `POST /confluence/backtest` - Test specific parameters
  - `POST /confluence/optimize` - Grid search for best parameters
- **UI**: `/confluence` page for strategy testing and optimization

#### 3. Forex Trading Support (Feature 3)
- **Forex-specific confluence strategy**: Optimized for major pairs (EURUSD, GBPUSD, USDJPY, etc.)
- **Forex Learning Agent**: Specialized agent that optimizes parameters across all major pairs
- **Endpoints**:
  - `POST /forex/confluence/backtest` - Backtest forex pair
  - `POST /forex/confluence/optimize` - Optimize single pair or all majors
  - `GET /forex/pairs` - List major forex pairs
- **UI**: `/forex` page for forex strategy testing

## Quickstart

### 1. Environment Setup

Create `.env` in the project root:
```bash
POLYGON_API_KEY=your_key
DATABASE_URL=postgresql+psycopg://user:pass@host/dbname
JWT_SECRET=superjwtsecret
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60
CORS_ALLOW_ORIGINS=http://localhost:3000
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD=YourStrongPass1
```

### 2. Database Setup

```bash
# Seed admin user (runs automatically on API startup, or manually):
python -m scripts.seed_admin
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Backend

```bash
uvicorn api.main:app --reload
```

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Access

- Frontend: http://localhost:3000
- API Docs: http://127.0.0.1:8000/docs
- Login with your `ADMIN_EMAIL` and `ADMIN_PASSWORD`

## API Endpoints

### Authentication
- `POST /auth/login` - Login and get JWT token

### Analysis
- `POST /analysis/signals` - Get technical indicators (SMA, RSI, candlestick patterns)
- `POST /analysis/chart` - Get OHLCV + indicators for plotting

### Backtesting
- `POST /backtest/sma-crossover` - Simple SMA crossover strategy
- `POST /confluence/backtest` - Multi-confirmation confluence strategy
- `POST /confluence/optimize` - Optimize confluence parameters

### Machine Learning
- `POST /ml/train/lstm` - Train LSTM model on price data
- `POST /ml/predict/lstm` - Predict next price using trained model

### Order Flow
- `GET /order-flow/large-orders` - Get large orders (>= $500k)
- `GET /order-flow/price-impact/{order_id}` - Get price impact snapshots
- `GET /order-flow/price-impact-stats` - Aggregate impact statistics

### Forex
- `POST /forex/confluence/backtest` - Backtest forex confluence strategy
- `POST /forex/confluence/optimize` - Optimize forex strategy (single or all pairs)
- `GET /forex/pairs` - List major forex pairs

### News
- `GET /news/sentiment/{ticker}` - Get aggregate news sentiment
- `GET /news/articles/{ticker}` - Get news articles with sentiment

## Project Structure

```
bot-trader/
├── api/                    # FastAPI application
│   ├── main.py            # App entry point
│   ├── routers/           # API endpoints
│   │   ├── auth.py        # Authentication
│   │   ├── analysis.py    # Technical analysis
│   │   ├── backtest.py    # SMA crossover
│   │   ├── confluence.py  # Confluence strategy
│   │   ├── forex.py       # Forex trading
│   │   ├── ml.py          # ML training/prediction
│   │   ├── news.py        # News sentiment
│   │   ├── orderflow.py   # Order flow tracking
│   │   └── models.py       # Model management
│   ├── models.py          # Database models (User, OrderFlow, PriceSnapshot)
│   ├── security.py       # JWT auth & password hashing
│   └── db.py              # Database connection
│
├── analysis_engine/        # Technical analysis
│   ├── candlestick_patterns.py  # Pattern detection
│   ├── indicators.py            # SMA, RSI
│   └── sentiment_analyzer.py    # FinBERT sentiment
│
├── backtester/            # Backtesting engine
│   ├── engine.py         # Backtrader wrapper
│   └── strategies/
│       ├── sma_crossover.py      # Simple strategy
│       ├── confluence.py         # Multi-confirmation (stocks)
│       └── forex_confluence.py  # Forex-optimized
│
├── data_ingestion/        # Data sources
│   ├── polygon_client.py  # Polygon.io client (stocks + forex)
│   ├── news_client.py    # News + sentiment
│   └── data_manager.py    # Data utilities
│
├── ml_models/             # Machine learning
│   ├── lstm_predictor.py  # LSTM model
│   ├── data_preprocessor.py
│   └── forex_learning_agent.py  # Forex optimization agent
│
├── order_flow/            # Order flow tracking
│   ├── aggregator.py     # Filter >= $500k orders
│   ├── price_tracker.py  # Price impact snapshots
│   └── streamer.py       # Real-time streamer (placeholder)
│
├── risk_management/      # Risk controls
│   ├── position_sizer.py
│   └── order_manager.py
│
├── config/                # Configuration
│   └── settings.py        # Environment variables
│
├── scripts/               # Utility scripts
│   └── seed_admin.py      # Seed admin user
│
└── frontend/              # Next.js UI
    └── src/app/
        ├── page.tsx       # Login
        ├── dashboard/     # Main dashboard
        ├── backtest/      # SMA backtest
        ├── train/         # ML training
        ├── confluence/    # Confluence strategy
        ├── forex/         # Forex trading
        └── orderflow/     # Order flow tracker
```

## Documentation

- **`SETUP.md`** - First time setup and local development
- **`DEPLOYMENT.md`** - Deploy to production (Vercel + Render + Neon)

## Advanced Features

### Enhanced Backtesting Engine

- **Risk Metrics**: Sharpe Ratio, Maximum Drawdown, Calmar Ratio, Alpha
- **Dynamic Slippage**: Volume and volatility-based execution costs
- **Risk Management**: Drawdown protection, position sizing, ATR-based stops
- **Enhanced Strategies**: See Enhanced SMA strategy in dashboard

### Position Sizing

- Optimal f (Ralph Vince)
- Kelly Criterion
- Risk-based sizing with stop loss distance

### Walk-Forward Analysis

- Out-of-sample validation
- Rolling window optimization
- Prevents overfitting
