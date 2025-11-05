# Quick Start: Get the UI Running

## Current Status Check

Your frontend has dependencies installed (node_modules exists). Let's verify everything works.

## Step 1: Check Backend is Ready

Make sure you have a `.env` file in the project root with:
- `POLYGON_API_KEY`
- `DATABASE_URL`
- `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- `JWT_SECRET`
- `CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

## Step 2: Start Backend (Terminal 1)

```bash
# From project root (not frontend directory)
cd /Users/pending.../bot-trader  # or wherever your project is

# Activate virtual environment
source .venv/bin/activate

# Start backend
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Keep this terminal open!**

## Step 3: Start Frontend (Terminal 2)

Open a NEW terminal:

```bash
# Navigate to frontend directory
cd /Users/pending.../bot-trader/frontend

# Start Next.js dev server
npm run dev
```

You should see:
```
✓ Ready in 2.3s
○ Local:        http://localhost:3000
```

## Step 4: Access the UI

1. Open your browser
2. Go to: **http://localhost:3000**
3. You should see the login page
4. Login with:
   - Email: Your `ADMIN_EMAIL` from `.env`
   - Password: Your `ADMIN_PASSWORD` from `.env`

## Step 5: Test It Works

1. **Login** - Should redirect to dashboard
2. **Dashboard** - Should load chart (may take a moment)
3. **Change ticker** - Try different stock (AAPL, MSFT, etc.)
4. **Run backtest** - Try the "Run Backtest" button

## Troubleshooting

### Frontend won't start?
```bash
cd frontend
npm install  # Reinstall dependencies
npm run dev
```

### Backend won't start?
- Check `.env` file exists
- Check port 8000 is free: `lsof -i :8000`
- Check virtual environment is activated
- Check database connection

### Can't login?
- Verify backend is running (check terminal 1)
- Check `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`
- Check backend logs for errors

### Frontend can't connect to backend?
- Make sure backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in frontend (should default to http://127.0.0.1:8000)
- Check browser console for errors (F12)

## Next: Once UI is Working

Once you have the UI running locally, we'll move to Docker Compose setup. See `GET_STARTED.md` for Docker Compose guide.

