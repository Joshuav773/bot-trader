# Bot Trader - Algorithmic Trading SaaS Platform

A production-ready algorithmic trading platform built with FastAPI and Next.js, featuring real-time market analysis, advanced backtesting, machine learning predictions, and order flow tracking.

## 🎯 What This Platform Does

**Bot Trader** is a comprehensive trading SaaS that allows you to:

1. **Analyze Markets** - Technical indicators, candlestick patterns, and sentiment analysis
2. **Backtest Strategies** - Test trading ideas on historical data with realistic costs
3. **Train ML Models** - Build and deploy LSTM models for price prediction
4. **Track Order Flow** - Monitor large institutional orders and their price impact
5. **Trade Forex** - Specialized strategies for currency markets

**Live Demo:**
- Frontend: https://bot-trader-xi.vercel.app
- Backend API: https://bot-trader-api.fly.dev
- API Documentation: https://bot-trader-api.fly.dev/docs

---

## ✨ Key Features

### 🔐 Authentication & Security
- **JWT-based authentication** - Secure token-based login
- **Single admin account** - Master account with full access
- **Password hashing** - Bcrypt for secure password storage
- **CORS protection** - Configured for production deployment

### 📊 Market Analysis
- **Technical Indicators**: SMA, EMA, RSI
- **Candlestick Patterns**: Hammer, Engulfing, Doji, Shooting Star
- **News Sentiment**: FinBERT-powered sentiment analysis
- **Multi-timeframe Support**: 5m, 15m, 30m, 1h, 4h, 1d

### 🧪 Backtesting Engine
- **SMA Crossover Strategy** - Classic moving average strategy
- **Bollinger Bands Mean Reversion** - Volatility-based trading
- **Confluence Strategy** - Multi-confirmation system requiring:
  - Trend confirmation (SMA crossover)
  - Momentum (RSI)
  - Volume confirmation
  - Candlestick patterns
  - News sentiment
- **Advanced Metrics**:
  - Sharpe Ratio, Maximum Drawdown, Calmar Ratio
  - Win rate, Profit Factor
  - Dynamic slippage modeling
  - Position sizing (Optimal f, Kelly Criterion)

### 🤖 Machine Learning
- **LSTM Price Prediction** - Train neural networks on historical data
- **Model Persistence** - Save and reuse trained models
- **Prediction API** - Get next-period price forecasts

### 📈 Order Flow Tracking
- **Large Order Detection** - Tracks orders ≥ $500k
- **Price Impact Analysis** - Measures price movements after large trades
- **Real-time Monitoring** - Live feed of institutional activity
- **Database Storage** - PostgreSQL for historical order flow data

### 💱 Forex Trading
- **Forex-Specific Strategies** - Optimized for currency pairs
- **Major Pairs Support** - EURUSD, GBPUSD, USDJPY, etc.
- **Forex Learning Agent** - Automated parameter optimization

---

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (Neon for production, SQLite for local dev)
- **ORM**: SQLModel
- **Authentication**: JWT tokens
- **ML Libraries**: TensorFlow (lazy-loaded), PyTorch (for FinBERT)
- **Data Sources**: Polygon.io (stocks & forex), ForexFactory (news)

### Frontend (Next.js)
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Charts**: Plotly.js
- **Deployment**: Vercel

### Infrastructure
- **Backend Hosting**: Fly.io (free tier available)
- **Frontend Hosting**: Vercel (free tier)
- **Database**: Neon PostgreSQL (free tier available)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL (or use Neon free tier)
- Polygon.io API key (free tier available)

### 1. Clone & Setup

```bash
git clone <repository-url>
cd bot-trader
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Or create manually
```

**Required Environment Variables** (`.env`):
```bash
# API Keys
POLYGON_API_KEY=your_polygon_key
ALPACA_API_KEY=your_alpaca_key  # Optional
ALPACA_SECRET_KEY=your_alpaca_secret  # Optional

# Database
DATABASE_URL=postgresql+psycopg://user:pass@host/dbname
# Or for local: sqlite:///./app.db

# Authentication
JWT_SECRET=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60

# CORS
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# Admin Account
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourSecurePassword123

# Polygon Data Limits (optional - defaults work for free tier)
POLYGON_LIMIT_5M=30
POLYGON_LIMIT_15M=60
POLYGON_LIMIT_30M=90
POLYGON_LIMIT_1H=730
POLYGON_LIMIT_4H=730
POLYGON_LIMIT_1D=3650

# Polygon retry / timeout tuning (optional)
POLYGON_MAX_RETRIES=3
POLYGON_RETRY_BACKOFF=1.5
POLYGON_READ_TIMEOUT=15
POLYGON_CONNECT_TIMEOUT=5

# Order flow streamer (optional)
ORDER_FLOW_POLL_INTERVAL=60          # seconds between polls
ORDER_FLOW_LOOKBACK_MINUTES=5        # how far back to fetch trades
ORDER_FLOW_MAX_TICKERS=25           # limit number of tickers to poll
# ORDER_FLOW_TICKERS=AAPL,MSFT,SPY   # optional custom list
# ML_MAX_ROWS=5000                   # Max rows used for LSTM training/prediction
```

### 3. Start Backend

```bash
# Option 1: Using the startup script
python start_server.py

# Option 2: Direct uvicorn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Using bash script
bash/bash/START_LOCAL.sh
```

Backend will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

### 4. Frontend Setup

```bash
cd frontend
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start dev server
npm run dev
```

Frontend will be available at: http://localhost:3000

### 5. Login

Use the credentials from your `.env` file:
- Email: `ADMIN_EMAIL`
- Password: `ADMIN_PASSWORD`

---

## 📚 API Documentation

### Authentication Endpoints

#### `POST /auth/login`
Login and receive JWT token.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "YourPassword"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Usage:** Include token in subsequent requests:
```
Authorization: Bearer <token>
```

### Analysis Endpoints

#### `POST /analysis/chart`
Get OHLCV data with technical indicators for charting.

**Request:**
```json
{
  "ticker": "AAPL",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "timeframe": "1d",
  "sma_length": 20,
  "ema_length": 20,
  "rsi_length": 14
}
```

**Response:** OHLCV arrays plus SMA, EMA, RSI values

#### `POST /analysis/signals`
Get trading signals (indicators + patterns).

### Backtesting Endpoints

#### `POST /backtest/sma-crossover`
Simple SMA crossover strategy backtest.

**Request:**
```json
{
  "ticker": "AAPL",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "timeframe": "1d",
  "fast_length": 10,
  "slow_length": 50,
  "cash": 10000
}
```

#### `POST /backtest/bbands`
Bollinger Bands mean-reversion strategy.

#### `POST /confluence/backtest`
Advanced confluence strategy (multi-confirmation).

#### `POST /confluence/optimize`
Optimize confluence strategy parameters via grid search.

### Machine Learning Endpoints

#### `POST /ml/train/lstm`
Train LSTM model on historical price data.

**Request:**
```json
{
  "ticker": "AAPL",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "window": 50,
  "horizon": 1,
  "units": 32,
  "epochs": 10,
  "batch_size": 32
}
```

**Response:** Model ID and training metrics

#### `POST /ml/predict/lstm`
Predict next price using trained model.

**Request:**
```json
{
  "model_id": "lstm_AAPL_2023-01-01_2024-01-01_w50_h1_u32",
  "ticker": "AAPL",
  "end_date": "2024-01-15",
  "window": 50
}
```

### Order Flow Endpoints

#### `GET /order-flow/large-orders`
Get recent large orders (≥ $500k).

**Query Parameters:**
- `hours` (int): Lookback period (default: 24)
- `ticker` (str, optional): Filter by ticker
- `order_type` (str, optional): "buy" or "sell"

#### `GET /order-flow/price-impact/{order_id}`
Get price impact snapshots for a specific order.

#### `GET /order-flow/price-impact-stats`
Aggregate statistics on price impact.

### Forex Endpoints

#### `POST /forex/confluence/backtest`
Backtest confluence strategy on forex pair.

#### `POST /forex/confluence/optimize`
Optimize forex strategy parameters (single pair or all majors).

#### `GET /forex/pairs`
List supported forex pairs.

### News Endpoints

#### `GET /news/sentiment/{ticker}`
Get aggregate news sentiment for ticker.

#### `GET /news/articles/{ticker}`
Get news articles with sentiment analysis.

---

## 📁 Project Structure

```
bot-trader/
├── api/                          # FastAPI backend
│   ├── main.py                  # Application entry point
│   ├── routers/                  # API endpoint handlers
│   │   ├── auth.py              # Authentication
│   │   ├── analysis.py          # Technical analysis
│   │   ├── backtest.py          # Backtesting strategies
│   │   ├── confluence.py        # Confluence strategy
│   │   ├── forex.py             # Forex trading
│   │   ├── ml.py                # ML training/prediction
│   │   ├── news.py              # News sentiment
│   │   ├── orderflow.py         # Order flow tracking
│   │   └── models.py            # Model management
│   ├── models.py                # Database models
│   ├── security.py              # JWT & password hashing
│   ├── db.py                    # Database connection
│   └── bootstrap.py             # Admin user creation
│
├── analysis_engine/             # Technical analysis tools
│   ├── indicators.py            # SMA, EMA, RSI
│   ├── candlestick_patterns.py  # Pattern detection
│   └── sentiment_analyzer.py    # FinBERT sentiment
│
├── backtester/                  # Backtesting framework
│   ├── engine.py                # Core backtesting engine
│   ├── advanced_engine.py       # Enhanced metrics
│   ├── metrics.py               # Performance metrics
│   ├── cost_model.py            # Slippage & commissions
│   ├── position_sizing.py       # Position sizing methods
│   ├── walk_forward.py          # Walk-forward analysis
│   └── strategies/               # Trading strategies
│       ├── base_strategy.py     # Base class
│       ├── sma_crossover.py     # Simple SMA
│       ├── bollinger_bands.py   # Mean reversion
│       ├── confluence.py        # Multi-confirmation (stocks)
│       └── forex_confluence.py  # Forex-optimized
│
├── data_ingestion/              # Data sources
│   ├── polygon_client.py        # Polygon.io API client
│   ├── news_client.py           # News aggregation
│   ├── forexfactory_client.py   # ForexFactory scraping
│   └── data_manager.py          # Data utilities
│
├── ml_models/                   # Machine learning
│   ├── lstm_predictor.py        # LSTM model (lazy-loaded)
│   ├── data_preprocessor.py     # Data preparation
│   └── forex_learning_agent.py  # Forex optimization
│
├── order_flow/                  # Order flow tracking
│   ├── aggregator.py            # Large order filtering
│   ├── price_tracker.py         # Price impact tracking
│   └── streamer.py              # Polygon REST streamer (Fly.io process)
│
├── risk_management/             # Risk controls
│   ├── position_sizer.py        # Position sizing
│   └── order_manager.py         # Order management
│
├── config/                      # Configuration
│   └── settings.py              # Environment variables
│
├── frontend/                    # Next.js frontend
│   ├── src/app/
│   │   ├── page.tsx             # Login page
│   │   ├── dashboard/           # Main dashboard
│   │   ├── train/               # ML training UI
│   │   ├── confluence/         # Confluence strategy UI
│   │   ├── forex/               # Forex trading UI
│   │   └── orderflow/           # Order flow tracker UI
│   └── src/components/
│       └── Navbar.tsx           # Navigation component
│
├── scripts/                     # Utility scripts
│   └── seed_admin.py            # Admin user seeding
│
├── bash/                        # Shell scripts
│   ├── START_LOCAL.sh          # Start backend locally
│   ├── START_FRONTEND.sh       # Start frontend locally
│   ├── STOP_BACKEND.sh          # Stop backend
│   └── STOP_FRONTEND.sh         # Stop frontend
│
├── Dockerfile                   # Docker image for backend
├── fly.toml                     # Fly.io configuration
├── requirements.txt             # Python dependencies
└── start_server.py              # Server startup script
```

---

## 🚢 Deployment

### Production Setup

**Frontend (Vercel):**
1. Connect GitHub repo to Vercel
2. Set environment variable: `NEXT_PUBLIC_API_URL=https://bot-trader-api.fly.dev`
3. Deploy automatically on push

**Backend (Fly.io):**
1. Install Fly CLI: `brew install flyctl` (or see [fly.io/docs](https://fly.io/docs))
2. Login: `flyctl auth login`
3. Create app: `flyctl launch` (or use existing)
4. Set secrets:
   ```bash
   flyctl secrets set \
     POLYGON_API_KEY=your_key \
     DATABASE_URL=your_neon_url \
     JWT_SECRET=your_secret \
     CORS_ALLOW_ORIGINS=https://bot-trader-xi.vercel.app \
     ADMIN_EMAIL=admin@example.com \
     ADMIN_PASSWORD=YourPassword
   ```
5. Deploy: `flyctl deploy` (the app process serves the API; the `streamer` process runs `python -m order_flow.streamer`)
6. Verify both processes: `flyctl status --app bot-trader-api` (should show `app` and `streamer`)

**Database (Neon):**
1. Sign up at [neon.tech](https://neon.tech)
2. Create database
3. Copy connection string to `DATABASE_URL` secret

### Environment Variables for Production

All the same variables as local `.env`, but set via:
- **Fly.io**: `flyctl secrets set KEY=value`
- **Vercel**: Dashboard → Settings → Environment Variables

---

## 🛠️ Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **SQLModel** - Database ORM (SQLAlchemy + Pydantic)
- **PostgreSQL** - Primary database (via Neon)
- **TensorFlow** - LSTM neural networks (lazy-loaded)
- **PyTorch** - FinBERT sentiment analysis
- **Backtrader** - Backtesting framework
- **Polygon.io** - Market data API
- **Uvicorn** - ASGI server

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Plotly.js** - Charting library

### Infrastructure
- **Fly.io** - Backend hosting
- **Vercel** - Frontend hosting
- **Neon** - Managed PostgreSQL

---

## 🎓 Key Concepts

### Confluence Strategy
A multi-confirmation trading strategy that requires multiple signals to align before entering a trade:
1. **Trend**: Price above/below moving averages
2. **Momentum**: RSI in favorable range
3. **Volume**: Above-average trading volume
4. **Patterns**: Bullish/bearish candlestick formations
5. **Sentiment**: Positive/negative news sentiment

This reduces false signals and improves win rate.

### Order Flow Tracking
Monitors large institutional orders (≥ $500k) and tracks their impact on price movements. Useful for:
- Identifying institutional activity
- Understanding price impact
- Following "smart money"

### Lazy Loading
TensorFlow is loaded only when needed (when ML endpoints are called), allowing the server to start quickly and handle CORS/auth requests immediately.

---

## 📝 Development Notes

### Adding New Strategies
1. Create strategy class in `backtester/strategies/`
2. Inherit from `BaseStrategy`
3. Implement `next()` method
4. Add endpoint in `api/routers/backtest.py`
5. Add UI component in `frontend/src/app/`

### Adding New Indicators
1. Add function in `analysis_engine/indicators.py`
2. Update `analysis_engine/__init__.py` if needed
3. Add to chart endpoint in `api/routers/analysis.py`
4. Update frontend chart component

### Database Schema
- **User**: Admin account (single master user)
- **OrderFlow**: Large orders (≥ $500k)
- **PriceSnapshot**: Price impact tracking

---

## 🐛 Troubleshooting

### CORS Errors
- Ensure `CORS_ALLOW_ORIGINS` includes your frontend URL
- Check Fly.io secrets are set correctly
- Hard refresh browser (Cmd+Shift+R)

### TensorFlow Issues
- TensorFlow loads lazily - server starts without it
- ML endpoints will fail until TensorFlow loads
- Check logs for TensorFlow initialization errors

### Database Connection
- Verify `DATABASE_URL` is correct
- Check Neon database is active
- Local dev uses SQLite if `DATABASE_URL` not set

### Login Issues
- Ensure `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set
- Admin user is created automatically on first startup
- Check database connection is working

---

## 📄 License

This project is proprietary. All rights reserved.

---

## 👥 Credits

Built with modern Python and JavaScript technologies for algorithmic trading.

**Questions?** Check the API docs at `/docs` or review the code structure above.
