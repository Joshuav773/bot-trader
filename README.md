# Bot Trader

FastAPI-based trading SaaS foundation for analysis, backtesting, ML, and risk management.

## Quickstart

1) Create `.env` in the project root:
```
POLYGON_API_KEY=your_key
DATABASE_URL=postgresql+psycopg://user:pass@host/dbname
JWT_SECRET=superjwtsecret
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60
CORS_ALLOW_ORIGINS=http://localhost:3000
```

2) Install dependencies:
```
pip install -r requirements.txt
```

3) Run the API from the project root:
```
uvicorn api.main:app --reload
```

4) Initialize master user (one-time):
```
curl -X POST http://127.0.0.1:8000/auth/init-master \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"YourStrongPass1"}'
```

5) Login to get JWT:
```
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"YourStrongPass1"}'
```
Use the `access_token` from the response as a Bearer token in subsequent requests.

### Example protected endpoints (use Authorization header)
- POST `/backtest/sma-crossover`
- POST `/analysis/signals`
- POST `/ml/train/lstm`
- POST `/ml/predict/lstm`

Example request:
```
curl -X POST "http://127.0.0.1:8000/backtest/sma-crossover" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","start_date":"2023-01-01","end_date":"2023-12-31"}'
```

Code lives under `api`, `analysis_engine`, `backtester`, `config`, `data_ingestion`, `ml_models`, `risk_management`, `tests`.
