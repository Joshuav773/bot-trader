# Bot Trader - Whale Order Watcher

**State-of-the-art real-time whale order detection system powered by Schwab Streaming API.**

A clean, production-ready FastAPI + Next.js application that streams real-time market data from Schwab to detect and alert on large institutional trades (≥ $500k).

---

## 🎯 Core Features

- **Real-time Streaming**: WebSocket-based streaming via Schwab API for instant whale detection
- **Whale Detection**: Automatically captures trades ≥ $500k with sub-second latency
- **Real-time Alerts**: Email and SMS notifications when whales are detected
- **Secure API**: JWT-based authentication with admin dashboard
- **Clean Architecture**: Schwab-only, no unnecessary dependencies
- **Production Ready**: Docker-first, ready for deployment

---

## 🏗️ Architecture

```
bot-trader/
├── api/                      # FastAPI backend
│   ├── main.py               # App bootstrap
│   ├── db.py                 # Database connection
│   ├── models.py             # User, OrderFlow models
│   ├── security.py           # JWT authentication
│   └── routers/
│       ├── auth.py           # Login endpoint
│       └── orderflow.py      # Whale order queries
├── data_ingestion/
│   └── schwab_stream_client.py  # Real-time streaming client
├── order_flow/
│   ├── aggregator.py         # Trade processing & filtering
│   └── alerts.py             # Email/SMS alert system
├── config/
│   └── settings.py           # Configuration management
└── frontend/                 # Next.js dashboard
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- Schwab Developer Portal account (free for Schwab account holders)
- PostgreSQL database (Neon recommended for free tier)

### Installation

```bash
# Clone repository
git clone <your-repo>
cd bot-trader

# Backend setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..
```

### Configuration

Create `.env` file:

```bash
# Schwab Streaming API (Required)
SCHWAB_APP_KEY=your_app_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=http://localhost

# Database
DATABASE_URL=postgresql+psycopg://user:pass@host/db

# Authentication
JWT_SECRET=your-secret-key-change-in-production
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=SecurePassword123

# CORS (for frontend)
CORS_ALLOW_ORIGINS=http://localhost:3000

# Alerts (Optional)
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_SMTP_HOST=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_SMTP_USER=your_email@gmail.com
ALERT_EMAIL_SMTP_PASSWORD=your_app_password
ALERT_EMAIL_FROM=your_email@gmail.com
ALERT_EMAIL_TO=recipient@example.com

ALERT_SMS_ENABLED=true
ALERT_SMS_PROVIDER=email_gateway
ALERT_SMS_EMAIL_GATEWAY=1234567890@vtext.com
```

### Run

```bash
# Terminal 1: Start backend
python start_server.py

# Terminal 2: Start streamer
python -m data_ingestion.schwab_stream_client

# Terminal 3: Start frontend
cd frontend
npm run dev
```

Visit `http://localhost:3000` and log in with your admin credentials.

---

## 📚 Setup Guides

### Schwab API Setup

See **[SCHWAB_STREAM_SETUP.md](./SCHWAB_STREAM_SETUP.md)** for:
- Creating Schwab Developer Portal app
- OAuth authorization flow
- Token management
- Troubleshooting

### Alert Configuration

See **[ALERTS_SETUP.md](./ALERTS_SETUP.md)** for:
- Email alerts (Gmail, SendGrid, etc.)
- SMS alerts (Twilio, email-to-SMS gateways)
- Configuration examples

---

## 🎯 How It Works

1. **Streaming**: Connects to Schwab WebSocket API for real-time level-one equity data
2. **Detection**: Calculates `Trade Value = Price × Size` for each trade
3. **Filtering**: Saves trades where `Trade Value ≥ $500,000`
4. **Alerts**: Sends email/SMS notifications immediately
5. **Storage**: Saves to PostgreSQL for historical analysis

---

## 📊 API Endpoints

### Authentication
- `POST /auth/login` - Admin login

### Order Flow
- `GET /order-flow/large-orders` - Query whale orders
  - Query params: `ticker`, `order_type`, `order_side`, `instrument`, `hours`

---

## 🛠️ Technology Stack

- **Backend**: FastAPI, SQLModel, PostgreSQL
- **Streaming**: schwab-py library (WebSocket)
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Alerts**: SMTP (email), Twilio/Email Gateway (SMS)
- **Deployment**: Docker, Azure Container Apps

---

## 📦 Dependencies

Minimal, production-focused dependencies:
- `fastapi` - Web framework
- `schwab-py` - Schwab API client
- `sqlmodel` - Database ORM
- `pandas` - Data processing
- `requests` - HTTP client (for alerts)

No heavy ML libraries, no unnecessary data providers.

---

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Environment variable secrets
- Database connection pooling

---

## 📝 License

[Your License Here]

---

## 🤝 Contributing

[Your Contributing Guidelines]

---

## 📞 Support

[Your Support Information]
