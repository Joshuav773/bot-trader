# Deployment Guide

Complete guide to deploy Bot Trader to production using free services.

## Architecture

- **Frontend**: Next.js on Vercel (free tier)
- **Backend**: FastAPI on Render (free tier)
- **Database**: PostgreSQL on Neon (free tier)

## Prerequisites

1. GitHub account (free)
2. Vercel account (free)
3. Render account (free)
4. Neon account (free)
5. Polygon.io API key

## Step 1: Push Code to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit"

# Create GitHub repo, then:
git remote add origin https://github.com/YOUR_USERNAME/bot-trader.git
git branch -M main
git push -u origin main
```

## Step 2: Setup Database (Neon)

1. Go to https://neon.tech and sign up
2. Click "Create Project"
3. Choose a name (e.g., `bot-trader-db`)
4. Select region closest to you
5. Click "Create Project"
6. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname
   ```
   **Save this for Step 3**

## Step 3: Deploy Backend (Render)

1. Go to https://render.com and sign up
2. Click "New +" → "Web Service"
3. Connect your GitHub account (if not connected)
4. Select your `bot-trader` repository
5. Configure service:
   - **Name**: `bot-trader-api`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: Leave empty (root)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python start_server.py`
   
   **Important**: Make sure `PORT` environment variable is set automatically by Render (it should be by default). The script will log if PORT is missing.
6. Click "Advanced" → Add Environment Variables:

   ```bash
   # API Keys
   POLYGON_API_KEY=your_polygon_key_here
   
   # Database (from Neon Step 2)
   DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname
   
   # JWT Security
   JWT_SECRET=generate-random-string-here-use-openssl-rand-hex-32
   JWT_ALGORITHM=HS256
   JWT_EXPIRES_MIN=60
   
   # CORS (will update after frontend deploy)
   CORS_ALLOW_ORIGINS=http://localhost:3000
   
   # Admin Account
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=YourSecurePassword123
   
   # Polygon Data Limits (days)
   POLYGON_LIMIT_5M=30
   POLYGON_LIMIT_15M=60
   POLYGON_LIMIT_30M=90
   POLYGON_LIMIT_1H=730
   POLYGON_LIMIT_4H=730
   POLYGON_LIMIT_1D=3650
   ```

7. Click "Create Web Service"
8. Wait for deployment (5-10 minutes)
9. Copy your service URL: `https://bot-trader-api.onrender.com`
   **Save this for Step 4**

## Step 4: Deploy Frontend (Vercel)

1. Go to https://vercel.com and sign up
2. Click "Add New" → "Project"
3. Import your GitHub repository `bot-trader`
4. Configure project:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto)
   - **Output Directory**: `.next` (auto)
5. Add Environment Variable:
   ```
   NEXT_PUBLIC_API_URL=https://bot-trader-api.onrender.com
   ```
   (Use your actual Render backend URL from Step 3)
6. Click "Deploy"
7. Wait for deployment (2-3 minutes)
8. Copy your Vercel URL: `https://your-app.vercel.app`
   **Save this for Step 5**

## Step 5: Connect Frontend to Backend

1. Go back to Render dashboard
2. Click on your `bot-trader-api` service
3. Go to "Environment" tab
4. Edit `CORS_ALLOW_ORIGINS`:
   ```
   http://localhost:3000,https://your-app.vercel.app
   ```
   (Replace with your actual Vercel URL)
5. Render will automatically redeploy
6. Wait for redeploy to complete (~2 minutes)

## Step 6: Verify Deployment

1. Visit your Vercel URL: `https://your-app.vercel.app`
2. You should see the login page
3. Login with:
   - Email: Your `ADMIN_EMAIL` from Step 3
   - Password: Your `ADMIN_PASSWORD` from Step 3
4. Test features:
   - Dashboard loads
   - Chart displays data
   - Backtest runs successfully

## Troubleshooting

### Backend Issues

**Service won't start:**
- Check Render logs: Service → "Logs" tab
- Verify all environment variables are set
- Check `DATABASE_URL` format is correct

**Database connection errors:**
- Verify Neon connection string is correct
- Check Neon dashboard for connection status
- Ensure database is not paused (Neon free tier pauses after inactivity)

**CORS errors:**
- Verify `CORS_ALLOW_ORIGINS` includes your Vercel URL
- Check for typos in the URL
- Wait for Render to finish redeploying

### Frontend Issues

**Can't connect to backend:**
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check backend is running (visit Render service URL)
- Check browser console for errors

**Build fails:**
- Check Vercel build logs
- Ensure all dependencies are in `package.json`
- Verify TypeScript types are installed

### Database Issues

**Neon database paused:**
- Free tier pauses after 1 week of inactivity
- Visit Neon dashboard to resume
- Connection will work automatically once resumed

## Environment Variables Reference

### Backend (Render)

| Variable | Example | Required |
|----------|---------|----------|
| `POLYGON_API_KEY` | `pk_test_123...` | Yes |
| `DATABASE_URL` | `postgresql://...` | Yes |
| `JWT_SECRET` | Random string | Yes |
| `JWT_ALGORITHM` | `HS256` | Yes |
| `JWT_EXPIRES_MIN` | `60` | Yes |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,https://app.vercel.app` | Yes |
| `ADMIN_EMAIL` | `admin@example.com` | Yes |
| `ADMIN_PASSWORD` | `SecurePass123` | Yes |
| `POLYGON_LIMIT_*` | `30`, `60`, `90`, `730`, `3650` | No (defaults provided) |

### Frontend (Vercel)

| Variable | Example | Required |
|----------|---------|----------|
| `NEXT_PUBLIC_API_URL` | `https://bot-trader-api.onrender.com` | Yes |

## Cost

All services used are **free tier**:
- **Vercel**: Free for hobby projects
- **Render**: Free tier (may spin down after inactivity)
- **Neon**: Free tier (pauses after 1 week inactivity, auto-resumes)

For production use, consider upgrading to paid tiers for:
- Always-on backend (Render)
- No database pauses (Neon)
- Higher rate limits

## Local Development

After deployment, you can still develop locally using the scripts in `bash/`:

```bash
# Start services
./bash/START_LOCAL.sh      # Backend on port 8000
./bash/START_FRONTEND.sh   # Frontend on port 3000

# Stop services
./bash/STOP_BACKEND.sh     # Stop backend
./bash/STOP_FRONTEND.sh    # Stop frontend
```

See `SETUP.md` for detailed local setup instructions.

