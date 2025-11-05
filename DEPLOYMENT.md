# Deployment Guide

## Frontend Deployment (Vercel)

The Next.js frontend can be deployed to Vercel easily.

### Option 1: Deploy via Vercel CLI

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy from frontend directory**:
   ```bash
   cd frontend
   vercel
   ```

4. **Follow the prompts**:
   - Link to existing project or create new
   - Set environment variables (see below)

### Option 2: Deploy via Vercel Dashboard

1. **Push code to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Go to [vercel.com](https://vercel.com)** and:
   - Click "New Project"
   - Import your GitHub repository
   - Set **Root Directory** to `frontend`
   - Configure environment variables (see below)

### Environment Variables for Frontend

Set these in Vercel Dashboard → Project Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

**Important**: Replace `your-backend-url.com` with your actual backend deployment URL.

### Build Settings

- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build` (auto-detected)
- **Output Directory**: `.next` (auto-detected)
- **Install Command**: `npm install` (auto-detected)

## Backend Deployment

The FastAPI backend needs to be deployed separately. Recommended options:

### Option 1: Render (Recommended)

1. **Create account at [render.com](https://render.com)**

2. **Create new Web Service**:
   - Connect your GitHub repository
   - **Root Directory**: (leave empty, or set to project root)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**:
   ```
   POLYGON_API_KEY=your_key
   ALPACA_API_KEY=your_key
   ALPACA_SECRET_KEY=your_secret
   DATABASE_URL=your_neon_postgres_url
   JWT_SECRET=your_secret_key
   JWT_ALGORITHM=HS256
   JWT_EXPIRES_MIN=60
   CORS_ALLOW_ORIGINS=https://your-vercel-frontend.vercel.app
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=YourPassword123
   POLYGON_LIMIT_5M=30
   POLYGON_LIMIT_15M=60
   POLYGON_LIMIT_30M=90
   POLYGON_LIMIT_1H=730
   POLYGON_LIMIT_4H=730
   POLYGON_LIMIT_1D=3650
   ```

4. **Update Frontend Environment Variable**:
   - In Vercel, set `NEXT_PUBLIC_API_URL` to your Render backend URL

### Option 2: Fly.io

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Create app**:
   ```bash
   fly launch
   ```

4. **Create `fly.toml`** (see below)

5. **Deploy**:
   ```bash
   fly deploy
   ```

### Option 3: Railway

1. **Create account at [railway.app](https://railway.app)**

2. **New Project** → **Deploy from GitHub**

3. **Add environment variables** (same as Render)

4. **Set start command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

## Quick Deploy Script

For Render deployment, create this file:

### `render.yaml` (for Render)

```yaml
services:
  - type: web
    name: bot-trader-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: POLYGON_API_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: JWT_SECRET
        generateValue: true
      - key: CORS_ALLOW_ORIGINS
        value: https://your-frontend.vercel.app
```

## Deployment Checklist

### Before Deploying Frontend:
- [ ] Set `NEXT_PUBLIC_API_URL` in Vercel environment variables
- [ ] Ensure backend is deployed and accessible
- [ ] Test API connectivity from frontend

### Before Deploying Backend:
- [ ] All API keys configured (Polygon, Alpaca)
- [ ] Database URL configured (Neon PostgreSQL)
- [ ] CORS origins include your frontend URL
- [ ] JWT secret set (use strong random string)
- [ ] Admin credentials configured

### After Deployment:
- [ ] Test login functionality
- [ ] Test API endpoints
- [ ] Verify CORS is working
- [ ] Check backend logs for errors
- [ ] Test a backtest to ensure everything works

## Troubleshooting

### Frontend can't connect to backend:
- Check `NEXT_PUBLIC_API_URL` is set correctly
- Verify backend is deployed and running
- Check CORS settings in backend
- Check browser console for errors

### Backend won't start:
- Check all environment variables are set
- Verify database connection
- Check logs for missing dependencies
- Ensure port is set correctly (use `$PORT` for cloud platforms)

### CORS errors:
- Add frontend URL to `CORS_ALLOW_ORIGINS` in backend
- Include protocol (https://)
- No trailing slashes

## Production Considerations

1. **Use HTTPS** for all deployments
2. **Set strong JWT_SECRET** (use random generator)
3. **Enable database backups** (Neon provides this)
4. **Monitor logs** for errors
5. **Set up alerts** for downtime
6. **Use environment-specific configs** (dev/staging/prod)

## Cost Estimates

- **Vercel**: Free tier available (Frontend)
- **Render**: Free tier available (Backend)
- **Neon**: Free tier available (Database)
- **Total**: Can run on free tiers for development/testing

