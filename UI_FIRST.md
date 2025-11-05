# Get UI Running First - Step by Step

## ✅ What You Have:
- ✓ Frontend code with dependencies installed
- ✓ Docker Compose files ready
- ✓ Backend code ready

## ⚠️ What You Need:
- `.env` file (environment variables)
- Python virtual environment (`.venv`)
- Backend dependencies installed

---

## Quick Setup (5 minutes)

### Step 1: Create `.env` File

```bash
# From project root
cd /Users/pending.../bot-trader

# Create .env file
cat > .env << 'EOF'
# API Keys (get from Polygon.io - free tier available)
POLYGON_API_KEY=your_polygon_key_here
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here

# Database (we'll use Docker Compose postgres later, for now use SQLite or external)
DATABASE_URL=sqlite:///./app.db

# JWT Settings
JWT_SECRET=change-me-to-random-secret-12345
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60

# CORS - Allow frontend
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Admin User
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123

# Polygon Data Limits
POLYGON_LIMIT_5M=30
POLYGON_LIMIT_15M=60
POLYGON_LIMIT_30M=90
POLYGON_LIMIT_1H=730
POLYGON_LIMIT_4H=730
POLYGON_LIMIT_1D=3650
EOF
```

**Edit the file** and add your actual API keys:
```bash
nano .env  # or use any text editor
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Start Backend (Terminal 1)

```bash
# Make sure you're in project root
cd /Users/pending.../bot-trader

# Activate virtual environment (if not already)
source .venv/bin/activate

# Start backend
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

**You should see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Keep this terminal open!**

### Step 4: Start Frontend (Terminal 2)

Open a **NEW terminal**:

```bash
# Navigate to frontend
cd /Users/pending.../bot-trader/frontend

# Start frontend (dependencies already installed)
npm run dev
```

**You should see:**
```
✓ Ready in 2.3s
○ Local:        http://localhost:3000
```

### Step 5: Access the UI

1. Open browser: **http://localhost:3000**
2. Login with:
   - Email: `admin@example.com` (or whatever you set in `.env`)
   - Password: `admin123` (or whatever you set in `.env`)

### Step 6: Test It

- ✅ Login works
- ✅ Dashboard loads
- ✅ Chart displays (try AAPL ticker)
- ✅ Backtest runs

---

## Once UI is Working: Docker Compose Next

After you see the UI working, we'll set up Docker Compose so you don't need to manage Python environment manually.

See `GET_STARTED.md` for Docker Compose guide.

---

## Troubleshooting

### "Module not found" errors?
```bash
# Backend
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Port 8000 already in use?
```bash
# Find what's using it
lsof -i :8000

# Kill it or use different port
uvicorn api.main:app --reload --host 127.0.0.1 --port 8001
```

### Database errors?
For now, using SQLite (no setup needed). Later with Docker Compose, we'll use PostgreSQL.

### Can't login?
- Check `.env` has `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- Check backend terminal for errors
- Try creating admin manually: `python -m scripts.seed_admin`

