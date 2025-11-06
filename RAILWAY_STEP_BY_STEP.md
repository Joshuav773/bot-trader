# Railway Deployment - Step by Step Guide

Follow these steps exactly to deploy your bot-trader backend to Railway.

## Prerequisites

✅ Your code is pushed to GitHub  
✅ You have a Neon PostgreSQL database (or create one)  
✅ You have your API keys ready (Polygon, etc.)

---

## Step 1: Create Railway Account

1. Go to **https://railway.app**
2. Click **"Start a New Project"** or **"Login"**
3. Choose **"Login with GitHub"** (recommended)
4. Authorize Railway to access your GitHub account

---

## Step 2: Create New Project

1. In Railway dashboard, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find and select your `bot-trader` repository
4. Click **"Deploy Now"**

Railway will automatically:
- Detect your Dockerfile
- Start building your app

---

## Step 3: Wait for Initial Build

This will take 2-4 minutes. You'll see:
- ✅ "Building" status
- ✅ "Deploying" status
- ✅ "Active" status when done

**Don't worry if the first deploy fails** - we need to set environment variables first.

---

## Step 4: Set Environment Variables

1. Click on your service (the box that appeared)
2. Go to **"Variables"** tab
3. Click **"+ New Variable"** for each one below

Add these variables (click **"Add"** after each):

### Required Variables

```
POLYGON_API_KEY
your_actual_polygon_key_here
```

```
DATABASE_URL
your_neon_postgresql_connection_string
```

```
JWT_SECRET
generate-a-random-secret-string-here-use-openssl-rand-hex-32
```

```
JWT_ALGORITHM
HS256
```

```
JWT_EXPIRES_MIN
60
```

```
CORS_ALLOW_ORIGINS
http://localhost:3000
```

```
ADMIN_EMAIL
admin@example.com
```

```
ADMIN_PASSWORD
YourSecurePassword123
```

### Optional Variables (Data Limits)

```
POLYGON_LIMIT_5M
30
```

```
POLYGON_LIMIT_15M
60
```

```
POLYGON_LIMIT_30M
90
```

```
POLYGON_LIMIT_1H
730
```

```
POLYGON_LIMIT_4H
730
```

```
POLYGON_LIMIT_1D
3650
```

### Port (Railway sets automatically, but add for safety)

```
PORT
8000
```

---

## Step 5: Get Your Database URL (Neon)

If you don't have a Neon database yet:

1. Go to **https://neon.tech**
2. Sign up (free)
3. Create new project
4. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/dbname
   ```
5. Paste it into Railway's `DATABASE_URL` variable

---

## Step 6: Configure Service Settings

1. Click on your service
2. Go to **"Settings"** tab
3. Check these settings:

### Build Settings
- **Build Command**: Leave empty (uses Dockerfile)
- **Start Command**: Leave empty (uses Dockerfile CMD)

### Network
- **Port**: Railway sets this automatically (usually 8000)
- **Public**: ✅ Enabled (for HTTP access)

---

## Step 7: Redeploy

After setting all environment variables:

1. Go to **"Deployments"** tab
2. Click **"Redeploy"** on the latest deployment
3. Or click **"Deploy"** button

Wait 2-4 minutes for build to complete.

---

## Step 8: Get Your Railway URL

1. In your service, go to **"Settings"** tab
2. Scroll to **"Domains"** section
3. You'll see your URL like:
   ```
   https://bot-trader-api.up.railway.app
   ```
4. Click **"Generate Domain"** if needed
5. **Copy this URL** - you'll need it for the frontend

---

## Step 9: Test Your API

1. Open your Railway URL in browser:
   ```
   https://your-app.up.railway.app
   ```
2. You should see:
   ```json
   {"message": "Welcome to the Trading SaaS API"}
   ```
3. Try the health endpoint:
   ```
   https://your-app.up.railway.app/health
   ```
   Should return:
   ```json
   {"status": "healthy", "service": "bot-trader-api"}
   ```

---

## Step 10: Update Frontend (Vercel)

1. Go to your **Vercel dashboard**
2. Select your frontend project
3. Go to **"Settings"** → **"Environment Variables"**
4. Update `NEXT_PUBLIC_API_URL`:
   ```
   https://your-app.up.railway.app
   ```
   (Replace with your actual Railway URL)
5. **Redeploy** your Vercel frontend

---

## Step 11: Update CORS (Important!)

In Railway, update the `CORS_ALLOW_ORIGINS` variable:

1. Go to Railway → Your service → Variables
2. Edit `CORS_ALLOW_ORIGINS`
3. Set it to:
   ```
   http://localhost:3000,https://your-vercel-frontend.vercel.app
   ```
   (Replace with your actual Vercel URL)
4. Railway will auto-redeploy

---

## Step 12: Verify Everything Works

1. Visit your Vercel frontend URL
2. Try to login with:
   - Email: Your `ADMIN_EMAIL`
   - Password: Your `ADMIN_PASSWORD`
3. If login works, you're all set! 🎉

---

## Troubleshooting

### Build Fails

**Check logs:**
1. Railway dashboard → Your service
2. Click on latest deployment
3. View "Build Logs" tab

**Common issues:**
- Missing environment variables → Add them
- Dockerfile error → Check Dockerfile syntax
- Requirements.txt error → Check Python dependencies

### Port Not Found

Railway sets `PORT` automatically. If you see errors:
- Make sure `start_server.py` exists
- Check Dockerfile CMD uses `start_server.py`
- Verify PORT variable is set (even if Railway overrides it)

### Database Connection Fails

- Verify `DATABASE_URL` is correct
- Check Neon database is not paused
- Ensure connection string format is correct

### CORS Errors

- Update `CORS_ALLOW_ORIGINS` with your Vercel URL
- Include both localhost and production URLs
- Wait for Railway to redeploy after updating

### Service Won't Start

**Check logs:**
1. Railway → Your service → "Deployments"
2. Click latest deployment → "Logs"
3. Look for error messages

**Common fixes:**
- Missing required env vars
- Database connection issues
- Port binding problems

---

## Monitoring Your Deployment

### View Logs
- Railway dashboard → Your service → "Deployments" → Click deployment → "Logs"

### Check Status
- Green "Active" = Running
- Yellow "Deploying" = Building
- Red "Failed" = Error (check logs)

### Metrics
- Railway dashboard shows CPU, Memory, Network usage
- Free tier has limits, but usually enough for small apps

---

## Free Tier Limits

- **500 hours/month** compute time
- **$5 credit** included
- **Auto-sleep** after inactivity (wakes up on request)
- Usually enough for development and small projects

---

## Next Steps

✅ Your backend is deployed!  
✅ Your frontend is connected!  
✅ Everything should work!

**If you need help:**
- Check Railway logs
- Check Vercel logs
- Verify all environment variables are set
- Test API endpoints directly

---

## Quick Reference

**Railway URL Format:**
```
https://your-app-name.up.railway.app
```

**Health Check:**
```
https://your-app-name.up.railway.app/health
```

**API Docs:**
```
https://your-app-name.up.railway.app/docs
```

**Update CORS:**
```
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-vercel.vercel.app
```

