# How to Run Bot Trader

## Quick Start (Daily Workflow)

### 1. Start Backend Server

Open a terminal in the project root:

```bash
cd /Users/pending.../bot-trader
source .venv/bin/activate  # Activate Python virtual environment
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

**What this does:**
- `source .venv/bin/activate` - Activates your Python virtual environment (where all Python packages are installed)
- `uvicorn api.main:app` - Starts the FastAPI server
- `--reload` - Auto-restarts when you change Python code
- `--host 127.0.0.1 --port 8000` - Runs on localhost port 8000

**You'll see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 2. Start Frontend Server

Open a **new terminal** (keep backend running):

```bash
cd /Users/pending.../bot-trader/frontend
npm run dev
```

**What this does:**
- `npm run dev` - Starts Next.js development server
- Runs on http://localhost:3000

**You'll see:**
```
✓ Ready in 2.3s
○ Local:        http://localhost:3000
```

### 3. Access the App

1. Open browser: http://localhost:3000
2. Login with credentials from your `.env` file:
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`

## Stopping the Servers

- **Backend**: Press `Ctrl+C` in the backend terminal
- **Frontend**: Press `Ctrl+C` in the frontend terminal

## First Time Setup

### 1. Install Python Dependencies

```bash
cd /Users/pending.../bot-trader
python3 -m venv .venv  # Create virtual environment (if not exists)
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Configure Environment

Create `.env` file in project root:

```bash
POLYGON_API_KEY=your_key_here
DATABASE_URL=postgresql+psycopg://user:pass@host/dbname
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60
CORS_ALLOW_ORIGINS=http://localhost:3000
ADMIN_EMAIL=admin@pendingmail.com
ADMIN_PASSWORD=YourPassword123
```

### 4. Database Setup

The admin user is created automatically on first backend startup.

Or manually:
```bash
source .venv/bin/activate
python -m scripts.seed_admin
```

## Troubleshooting

### Backend won't start?
- Check if port 8000 is already in use: `lsof -i :8000`
- Make sure virtual environment is activated
- Check `.env` file exists and has required variables

### Frontend won't start?
- Make sure you're in `frontend/` directory
- Run `npm install` if you see module errors
- Clear cache: `rm -rf .next node_modules/.cache`

### Can't login?
- Check backend is running: `curl http://127.0.0.1:8000/`
- Verify `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`
- Check backend logs for errors

## Development Tips

**Backend auto-reloads** when you change Python files (thanks to `--reload`)

**Frontend auto-reloads** when you change React/Next.js files

**API Documentation** available at: http://127.0.0.1:8000/docs

