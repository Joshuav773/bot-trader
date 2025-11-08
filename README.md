# Bot Trader (Watcher Edition)

Lightweight FastAPI + Next.js stack focused on two capabilities:

- **Backtesting dashboard** powered by Polygon.io data and Backtrader strategies.
- **Large order watcher** that polls Polygon REST endpoints, stores trades in Postgres, and exposes the order-flow dashboard.

All heavy ML/forex/news modules were removed to keep hosting costs near $0 on Azure Container Apps.

---

## Core Features

- **Secure admin login** with JWT tokens and single master account bootstrap.
- **Dashboard API**: historical bars with SMA/EMA/RSI plus three ready-to-run strategies (SMA crossover, Bollinger, enhanced SMA).
- **Order Flow API**: query large trades, price impact snapshots, and aggregated stats.
- **Polygon-based streamer**: async polling loop that captures trades ≥ $500k and writes to Postgres/Neon.
- **Docker-first deployment** with GitHub Actions workflow pushing to Azure Container Registry (ACR).
- **Next.js UI** trimmed to login, dashboard, and order-flow pages only.

---

## Project Layout

```
bot-trader/
├── api/                   # FastAPI backend
│   ├── main.py            # App bootstrap (CORS, health, routers)
│   ├── db.py              # SQLModel engine + session helpers
│   ├── models.py          # User, OrderFlow, PriceSnapshot tables
│   ├── security.py        # JWT helpers, password hashing
│   ├── bootstrap.py       # Admin-user seeding
│   └── routers/           # Active routers (auth, analysis, backtest, orderflow)
├── analysis_engine/       # Indicator utilities (SMA/EMA/RSI, patterns)
├── backtester/            # Backtrader engines, metrics, strategies
├── data_ingestion/        # Polygon REST client + dataframe utilities
├── order_flow/            # Large-order aggregator + polling streamer
├── config/settings.py     # Environment variable parsing
├── frontend/              # Next.js 14 app (login, dashboard, orderflow)
├── Dockerfile             # Slim Python 3.12 image for backend
├── requirements.txt       # Minimal Python dependency set
└── .github/workflows/     # CI build → push image to Azure Container Registry
```

---

## Local Development

### Prerequisites

- Python 3.12
- Node.js 18+
- Polygon.io API key (free tier works)
- Postgres/Neon connection string (SQLite fallback for quick tests)

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env  # or create manually
python start_server.py
```

Key `.env` variables:

```
POLYGON_API_KEY=pk_your_key
DATABASE_URL=postgresql+psycopg://user:pass@host/db   # Neon recommended
JWT_SECRET=change-me
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=SuperSecure123
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
ORDER_FLOW_POLL_INTERVAL=60          # seconds between polls
ORDER_FLOW_LOOKBACK_MINUTES=5
ORDER_FLOW_MAX_TICKERS=10
# ORDER_FLOW_TICKERS=AAPL,SPY,MSFT   # optional custom list
```

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Visit `http://localhost:3000`, log in with the admin credentials, and access `/dashboard` or `/orderflow`.

---

## Azure Deployment (Watcher Only)

1. **Build + Push via GitHub Actions**
   - Repository secrets already expected:
     - `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
     - `AZURE_CONTAINER_REGISTRY` (e.g. `bottraderacr.azurecr.io`)
     - `IMAGE_NAME` (e.g. `bot-trader/watcher`)
   - Workflow: `.github/workflows/push-to-acr.yml`
   - On push to `main`, GitHub builds `Dockerfile` and pushes `latest` + commit SHA tags to ACR.

2. **Create Azure Container Apps environment**
   - Azure Portal → *Container Apps* → *Create*.
   - Resource Group: `bottrader-rg`.
   - Environment name: e.g. `bottrader-env` (East US).

3. **Create Container App**
   - Container Apps → *Create app* → pick `bottrader-env`.
   - Image source: `Azure Container Registry` → select `bottraderacr`.
   - Image: choose `bot-trader/watcher:latest`.
   - Ingress: enable external, port `8000`.
   - Scale: min replicas `0`, max `1` (consumption plan keeps cost ≈ $0).

4. **Configure Secrets/Env**
   - Under *Revisions → Secrets*, add `POLYGON_API_KEY`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `JWT_SECRET`, etc.
   - Map them as environment variables; add plain vars like `WATCHER_ONLY=true`, `ORDER_FLOW_POLL_INTERVAL=60`.

5. **Smoke Test**
   - Open the Container App URL → `/health` should return `{"status": "healthy"}`.
   - Use `/docs` to try `/order-flow/large-orders` and `/analysis/chart`.

6. **Point Frontend**
   - Update Vercel `NEXT_PUBLIC_API_URL` (or local `.env.local`) to the Container App URL.

---

## GitHub Actions Workflow

`push-to-acr.yml` steps:

1. Checkout repo.
2. Authenticate to Azure with the service principal.
3. Login to ACR (`az acr login`).
4. `docker build` using the trimmed Dockerfile.
5. Push `latest` and `<commit>` tags.

This keeps the registry updated so the Container App can be redeployed by switching the tag in the Azure Portal or via `az containerapp revision create`.

---

## API Overview

- `POST /auth/login` – obtain JWT (admin only).
- `POST /analysis/chart` – OHLCV + SMA/EMA/RSI arrays.
- `POST /analysis/signals` – last few indicator readings & candlestick flags.
- `POST /backtest/sma-crossover` – run Backtrader SMA strategy.
- `POST /backtest/bollinger-bands`
- `POST /backtest/enhanced-sma`
- `GET /order-flow/large-orders` – recent trades ≥ $500k.
- `GET /order-flow/price-impact/{order_id}`
- `GET /order-flow/price-impact-stats`
- `POST /order-flow/trigger-snapshots/{order_id}` – manual refresh (testing).

All routes (except `/health`, `/docs`) require `Authorization: Bearer <token>`.

---

## Deployment Tips

- **Database**: Neon free tier works well; store the pooled connection string in `DATABASE_URL`.
- **CORS**: keep `CORS_ALLOW_ORIGINS` synchronized between Azure secrets and frontend environment.
- **Streamer**: For production reliability consider a second Container App instance running only `python -m order_flow.streamer`. For now the polling loop can run inside the main app process.
- **Scaling**: Container Apps consumption plan spins down to zero. First request may take a few seconds while the container warms up; set frontend loaders accordingly.

---

## License

All rights reserved. Internal use only.
