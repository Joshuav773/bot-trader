# Free Deployment - Step by Step Guide

## Prerequisites
- GitHub account (free)
- Polygon.io API key (free tier available)
- 30 minutes of your time

## Step 1: Push Code to GitHub

### A. Initialize Git (if not done)
```bash
cd /Users/pending.../bot-trader
git init
git add .
git commit -m "Initial commit"
```

### B. Create GitHub Repo
1. Go to https://github.com/new
2. Create new repository (name it `bot-trader` or whatever you want)
3. **Don't** initialize with README
4. Copy the commands GitHub shows you

### C. Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/bot-trader.git
git branch -M main
git push -u origin main
```

---

## Step 2: Set Up Database (Neon) - FREE

1. Go to https://neon.tech
2. Sign up with GitHub (free)
3. Click "Create Project"
4. Name it: `bot-trader-db`
5. Region: Choose closest to you
6. Click "Create Project"
7. **Copy the connection string** - looks like:
   ```
   postgresql://user:password@host.neon.tech/dbname?sslmode=require
   ```
8. **Save this somewhere** - you'll need it in Step 3

**That's it for database!** Neon is free and ready.

---

## Step 3: Deploy Backend (Render) - FREE

1. Go to https://render.com
2. Sign up with GitHub (free)
3. Click "New +" → "Web Service"
4. Connect your GitHub account (if not already)
5. Select your `bot-trader` repository
6. Click "Connect"

### Configure Backend:

**Name:** `bot-trader-api`

**Region:** Choose closest to you

**Branch:** `main`

**Root Directory:** (leave empty - it's the project root)

**Environment:** `Python 3`

**Build Command:** 
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### Add Environment Variables:

Click "Advanced" → "Add Environment Variable" and add these:

```
POLYGON_API_KEY = your_polygon_key_here
ALPACA_API_KEY = (optional, can leave empty)
ALPACA_SECRET_KEY = (optional, can leave empty)
DATABASE_URL = paste_your_neon_connection_string_here
JWT_SECRET = generate-a-random-string-here-12345
JWT_ALGORITHM = HS256
JWT_EXPIRES_MIN = 60
CORS_ALLOW_ORIGINS = http://localhost:3000
ADMIN_EMAIL = admin@example.com
ADMIN_PASSWORD = YourSecurePassword123
POLYGON_LIMIT_5M = 30
POLYGON_LIMIT_15M = 60
POLYGON_LIMIT_30M = 90
POLYGON_LIMIT_1H = 730
POLYGON_LIMIT_4H = 730
POLYGON_LIMIT_1D = 3650
```

**Important:** 
- Replace `your_polygon_key_here` with your actual Polygon.io key
- Replace `paste_your_neon_connection_string_here` with the Neon connection string from Step 2
- Generate a random string for `JWT_SECRET` (use a password generator)

### Deploy:

7. Scroll down and click **"Create Web Service"**
8. Wait 5-10 minutes for first build
9. Once done, you'll get a URL like: `https://bot-trader-api.onrender.com`
10. **Copy this URL** - you'll need it for frontend

**Test it works:**
- Visit: `https://your-backend-url.onrender.com/`
- Should see: `{"message": "Welcome to the Trading SaaS API"}`

---

## Step 4: Deploy Frontend (Vercel) - FREE

1. Go to https://vercel.com
2. Sign up with GitHub (free)
3. Click "Add New..." → "Project"
4. Import your `bot-trader` repository
5. Click "Import"

### Configure Frontend:

**Framework Preset:** Next.js (auto-detected)

**Root Directory:** Click "Edit" and set to `frontend`

**Environment Variables:** Click "Add" and add:
```
NEXT_PUBLIC_API_URL = https://your-backend-url.onrender.com
```
(Replace with your actual Render backend URL from Step 3)

### Deploy:

6. Click **"Deploy"**
7. Wait 2-3 minutes
8. Once done, you'll get a URL like: `https://bot-trader-xyz.vercel.app`
9. **Copy this URL** - this is your live app!

---

## Step 5: Connect Frontend to Backend

Now we need to tell the backend to accept requests from your Vercel frontend:

1. Go back to Render dashboard
2. Click on your `bot-trader-api` service
3. Go to "Environment" tab
4. Find `CORS_ALLOW_ORIGINS`
5. Edit it to include your Vercel URL:
   ```
   http://localhost:3000,https://your-vercel-app.vercel.app
   ```
   (Replace with your actual Vercel URL)
6. Click "Save Changes"
7. Render will automatically redeploy

---

## Step 6: Test Everything

1. Visit your Vercel URL: `https://your-app.vercel.app`
2. You should see the login page
3. Login with:
   - Email: `admin@example.com` (or what you set in Render)
   - Password: `YourSecurePassword123` (or what you set in Render)
4. Should redirect to dashboard
5. Try loading a chart
6. Try running a backtest

**If it works - you're done! 🎉**

---

## Troubleshooting

### Frontend shows "Failed to fetch"?
- Check `NEXT_PUBLIC_API_URL` in Vercel matches your Render URL
- Check backend is running (visit Render URL directly)
- Check CORS includes your Vercel URL

### Can't login?
- Check `ADMIN_EMAIL` and `ADMIN_PASSWORD` in Render
- Check backend logs in Render dashboard

### Backend won't start?
- Check all environment variables are set in Render
- Check logs in Render dashboard for errors
- Make sure `DATABASE_URL` is correct (from Neon)

---

## Cost Summary

- **Neon Database**: FREE (512 MB storage, sufficient for testing)
- **Render Backend**: FREE (750 hours/month, auto-sleeps after 15min inactivity)
- **Vercel Frontend**: FREE (unlimited deployments)
- **Total**: $0/month

---

## Next Steps

Once everything is working:
1. Share your Vercel URL with your friend
2. They can login and use the app
3. If backend sleeps (Render free tier), first request takes ~30 seconds to wake up

That's it! Everything is free and your app is live on the internet! 🚀

