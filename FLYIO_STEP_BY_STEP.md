# Fly.io Deployment - Step by Step Guide

Fly.io has a **web dashboard** for viewing logs, metrics, and managing apps, but initial setup requires CLI. This guide covers both.

---

## Fly.io UI Overview

✅ **Web Dashboard** (https://fly.io/dashboard):
- View apps and status
- View logs
- View metrics
- Manage secrets (environment variables)
- View deployments

⚠️ **CLI Required For:**
- Initial setup
- Deploying
- Some advanced features

---

## Prerequisites

✅ Your code is pushed to GitHub  
✅ You have a Neon PostgreSQL database  
✅ You have your API keys ready

---

## Step 1: Install Fly CLI

### macOS (You're on macOS):

```bash
curl -L https://fly.io/install.sh | sh
```

This installs `fly` command. Add to PATH if needed:

```bash
# Add to your ~/.zshrc or ~/.bashrc
export PATH="$HOME/.fly/bin:$PATH"
```

Then reload:
```bash
source ~/.zshrc
```

### Verify Installation:

```bash
fly version
```

You should see version number.

---

## Step 2: Sign Up / Login

### Option A: Via CLI (Recommended)

```bash
fly auth login
```

This will:
1. Open browser
2. Ask you to sign up/login
3. Authorize CLI access

### Option B: Via Web

1. Go to https://fly.io
2. Sign up with email/GitHub
3. Then run `fly auth login` to link CLI

---

## Step 3: Initialize Your App

Navigate to your project directory:

```bash
cd /Users/pending.../bot-trader
```

### Check if fly.toml exists:

```bash
ls -la fly.toml
```

If it exists, you can use it. If not, create it:

```bash
fly launch
```

This will:
- Detect your Dockerfile
- Ask for app name (use: `bot-trader-api` or your choice)
- Ask for region (choose closest to you)
- Create `fly.toml` file

**Answer prompts:**
- App name: `bot-trader-api` (or your choice)
- Region: Choose closest (e.g., `iad` for US East)
- Postgres: Say "No" (we're using Neon)
- Redis: Say "No"

---

## Step 4: Verify fly.toml

Your `fly.toml` should look like this (already exists):

```toml
app = "bot-trader-api"
primary_region = "iad"

[build]

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[services]]
  protocol = "tcp"
  internal_port = 8000

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]
```

This is already correct! ✅

---

## Step 5: Set Environment Variables (Secrets)

Fly.io uses "secrets" for environment variables. Set them via CLI:

```bash
# Required secrets
fly secrets set POLYGON_API_KEY=your_actual_key_here
fly secrets set DATABASE_URL=your_neon_connection_string
fly secrets set JWT_SECRET=generate-random-secret-here
fly secrets set JWT_ALGORITHM=HS256
fly secrets set JWT_EXPIRES_MIN=60
fly secrets set CORS_ALLOW_ORIGINS=http://localhost:3000
fly secrets set ADMIN_EMAIL=admin@example.com
fly secrets set ADMIN_PASSWORD=YourSecurePassword123

# Optional: Data limits
fly secrets set POLYGON_LIMIT_5M=30
fly secrets set POLYGON_LIMIT_15M=60
fly secrets set POLYGON_LIMIT_30M=90
fly secrets set POLYGON_LIMIT_1H=730
fly secrets set POLYGON_LIMIT_4H=730
fly secrets set POLYGON_LIMIT_1D=3650
```

**Note:** Replace values with your actual:
- Polygon API key
- Neon database URL
- Strong JWT secret (generate with: `openssl rand -hex 32`)
- Your admin email/password

---

## Step 6: Verify Dockerfile

Make sure your `Dockerfile` uses `start_server.py`:

```dockerfile
CMD ["python", "start_server.py"]
```

This is already correct! ✅

---

## Step 7: Deploy!

```bash
fly deploy
```

This will:
1. Build Docker image (1-3 minutes)
2. Push to Fly.io
3. Deploy to edge locations
4. Give you a URL

**First deploy takes 2-4 minutes** (subsequent deploys are faster)

---

## Step 8: Get Your URL

After deployment, you'll see:

```
App: bot-trader-api
URL: https://bot-trader-api.fly.dev
```

**Or check via CLI:**

```bash
fly status
```

**Or via Web Dashboard:**
1. Go to https://fly.io/dashboard
2. Click on your app
3. See URL in the overview

---

## Step 9: Test Your API

1. **Health check:**
   ```
   https://bot-trader-api.fly.dev/health
   ```
   Should return: `{"status": "healthy", "service": "bot-trader-api"}`

2. **Root endpoint:**
   ```
   https://bot-trader-api.fly.dev/
   ```
   Should return: `{"message": "Welcome to the Trading SaaS API"}`

---

## Step 10: Update CORS for Frontend

Update CORS to include your Vercel URL:

```bash
fly secrets set CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-vercel-app.vercel.app
```

(Replace with your actual Vercel URL)

---

## Step 11: Update Frontend (Vercel)

1. Go to Vercel dashboard
2. Settings → Environment Variables
3. Update `NEXT_PUBLIC_API_URL`:
   ```
   https://bot-trader-api.fly.dev
   ```
4. Redeploy frontend

---

## Step 12: Verify Everything Works

1. Visit your Vercel frontend
2. Try to login
3. Test dashboard features
4. Everything should work! 🎉

---

## Using Fly.io Web Dashboard

### Access Dashboard:

1. Go to https://fly.io/dashboard
2. Login
3. See all your apps

### View Logs:

1. Click on your app
2. Go to "Logs" tab
3. Real-time logs

### View Metrics:

1. Click on your app
2. Go to "Metrics" tab
3. CPU, Memory, Network usage

### Manage Secrets:

**Via Web:**
1. Click on your app
2. Go to "Secrets" tab
3. Add/Edit/Delete secrets

**Via CLI:**
```bash
fly secrets list
fly secrets set KEY=value
fly secrets unset KEY
```

### View Deployments:

1. Click on your app
2. Go to "Deployments" tab
3. See all deployments and status

---

## Useful CLI Commands

```bash
# View logs
fly logs

# Check status
fly status

# Open app in browser
fly open

# View secrets
fly secrets list

# Set secret
fly secrets set KEY=value

# Deploy
fly deploy

# SSH into app
fly ssh console

# Scale (if needed)
fly scale count 1
```

---

## Troubleshooting

### Build Fails

**Check logs:**
```bash
fly logs
```

**Common issues:**
- Dockerfile error → Check Dockerfile syntax
- Requirements.txt error → Check Python dependencies
- Missing files → Check Dockerfile COPY commands

### App Won't Start

**Check logs:**
```bash
fly logs
```

**Check status:**
```bash
fly status
```

**Common issues:**
- Missing secrets → Set all required secrets
- Database connection → Check DATABASE_URL
- Port binding → Check start_server.py reads PORT

### Port Issues

Fly.io sets `PORT` automatically. Your `start_server.py` already handles this ✅

### Database Connection

- Verify `DATABASE_URL` secret is correct
- Check Neon database is not paused
- Ensure connection string format is correct

### CORS Errors

- Update `CORS_ALLOW_ORIGINS` with your Vercel URL
- Include both localhost and production URLs
- Redeploy after updating secrets

---

## Free Tier Limits

- **3 shared-cpu-1x VMs** (256MB RAM each)
- **160GB outbound data/month**
- **Auto-sleep** after inactivity (very fast wake-up ~5 sec)
- **Global edge deployment** (free!)

---

## Monitoring

### Via Web Dashboard:

1. Go to https://fly.io/dashboard
2. Click your app
3. View:
   - Real-time logs
   - CPU/Memory metrics
   - Network usage
   - Deployment history

### Via CLI:

```bash
fly status      # App status
fly logs        # Real-time logs
fly metrics     # Performance metrics
```

---

## Next Steps

✅ Your backend is deployed on Fly.io!  
✅ Fastest builds (1-3 minutes)  
✅ Global edge deployment  
✅ Web dashboard for monitoring  

**Benefits:**
- ⚡ Fastest deployments
- 🌍 Global edge (low latency)
- 📊 Web dashboard for monitoring
- 🔧 CLI for deployment

---

## Quick Reference

**Your App URL:**
```
https://bot-trader-api.fly.dev
```

**Health Check:**
```
https://bot-trader-api.fly.dev/health
```

**API Docs:**
```
https://bot-trader-api.fly.dev/docs
```

**Dashboard:**
```
https://fly.io/dashboard
```

---

## Summary

**Fly.io has:**
- ✅ Web dashboard for viewing/managing
- ⚠️ CLI required for deployment
- ✅ Best performance (fastest builds)
- ✅ Global edge deployment

**You're all set!** Your app is now on Fly.io with the fastest deployments! 🚀

