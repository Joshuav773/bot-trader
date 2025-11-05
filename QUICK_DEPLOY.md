# Quick Vercel Deployment Guide

## Deploy Frontend to Vercel (5 minutes)

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Login
```bash
vercel login
```

### Step 3: Deploy
```bash
cd frontend
vercel
```

### Step 4: Set Environment Variable
After deployment, go to your Vercel project dashboard:

1. Settings → Environment Variables
2. Add: `NEXT_PUBLIC_API_URL` = `https://your-backend-url.com`
   - Replace with your actual backend URL (Render/Railway/Fly.io)

### Step 5: Redeploy
```bash
vercel --prod
```

That's it! Your frontend is live.

---

## Backend Deployment Options

### Option A: Render (Easiest - Free Tier Available)

1. Go to [render.com](https://render.com) and sign up
2. Click "New" → "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Name**: `bot-trader-api`
   - **Root Directory**: (leave empty)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

5. Add Environment Variables (see full list in DEPLOYMENT.md)

6. Deploy! Your backend URL will be: `https://bot-trader-api.onrender.com`

### Option B: Railway (Also Easy)

1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Select your repo
4. Add environment variables
5. Deploy!

### Option C: Fly.io

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch (follow prompts)
fly launch

# Deploy
fly deploy
```

---

## Required Environment Variables

### Backend (Render/Railway/Fly.io):
```
POLYGON_API_KEY=your_key
DATABASE_URL=your_neon_postgres_url
JWT_SECRET=generate-random-string-here
CORS_ALLOW_ORIGINS=https://your-vercel-app.vercel.app
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourPassword123
```

### Frontend (Vercel):
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

---

## Quick Test After Deployment

1. **Frontend**: Visit your Vercel URL
2. **Login**: Use your ADMIN_EMAIL and ADMIN_PASSWORD
3. **Test**: Try running a backtest on the dashboard

If login fails, check:
- Backend is running and accessible
- CORS_ALLOW_ORIGINS includes your Vercel URL
- NEXT_PUBLIC_API_URL is set correctly

---

## Need Help?

See `DEPLOYMENT.md` for detailed instructions and troubleshooting.

