# How Vercel Frontend Connects to Backend

## The Setup

When you deploy frontend to Vercel, it's running on a different server (Vercel's servers) than your backend. They need to communicate over the internet.

## How It Works

### 1. Frontend Configuration (Vercel)

The frontend uses an environment variable to know where your backend is:

```typescript
// In frontend code (e.g., dashboard/page.tsx)
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
```

**When deployed to Vercel:**
- Set `NEXT_PUBLIC_API_URL` = your backend URL (e.g., `https://your-backend.onrender.com`)
- Frontend will use this URL to make API calls

### 2. Backend Configuration (Your Server)

The backend needs to allow requests from your Vercel frontend URL:

```python
# In config/settings.py
CORS_ALLOW_ORIGINS = [
    "http://localhost:3000",  # Local development
    "https://your-app.vercel.app",  # Your Vercel frontend
]
```

## Complete Setup Guide

### Step 1: Deploy Backend First

Deploy your backend to one of these (using Docker Compose or other method):

**Option A: Render (Free Tier)**
- URL: `https://bot-trader-api.onrender.com`

**Option B: Fly.io (Free Tier)**
- URL: `https://bot-trader-api.fly.dev`

**Option C: Railway**
- URL: `https://bot-trader-api.railway.app`

**Option D: Your Own Server (VPS)**
- URL: `https://api.yourdomain.com`

### Step 2: Configure Backend CORS

In your backend `.env` file (or Docker Compose environment):

```bash
# Add your Vercel frontend URL
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

**Important:** Replace `your-app.vercel.app` with your actual Vercel URL.

### Step 3: Deploy Frontend to Vercel

1. **Deploy to Vercel** (via CLI or GitHub)
2. **Set Environment Variable** in Vercel Dashboard:
   - Go to: Project Settings → Environment Variables
   - Add: `NEXT_PUBLIC_API_URL` = `https://your-backend-url.com`
   - Replace with your actual backend URL

3. **Redeploy** (Vercel will rebuild with new env var)

### Step 4: Test Connection

1. Visit your Vercel frontend: `https://your-app.vercel.app`
2. Try to login
3. Check browser console (F12) for errors
4. If CORS error appears, add Vercel URL to backend's `CORS_ALLOW_ORIGINS`

## Visual Flow

```
┌─────────────────────┐         HTTP Request         ┌─────────────────────┐
│                     │ ───────────────────────────> │                     │
│  Vercel Frontend    │                              │  Your Backend       │
│  (your-app.vercel)  │ <────────────────────────── │  (render/fly/etc)  │
│                     │      JSON Response           │                     │
└─────────────────────┘                              └─────────────────────┘
         │                                                      │
         │                                                      │
    Uses env var:                                        Checks CORS:
    NEXT_PUBLIC_API_URL                                 CORS_ALLOW_ORIGINS
    = https://backend...                                 includes Vercel URL
```

## Example Configuration

### Backend `.env` (Docker Compose or server):
```bash
# CORS - Allow both local and Vercel
CORS_ALLOW_ORIGINS=http://localhost:3000,https://bot-trader-xyz.vercel.app

# Your other settings...
POLYGON_API_KEY=your_key
DATABASE_URL=your_db_url
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourPassword
```

### Vercel Environment Variables:
```
NEXT_PUBLIC_API_URL=https://bot-trader-api.onrender.com
```

## Troubleshooting

### "CORS policy" error?
**Problem:** Backend doesn't allow your Vercel URL

**Solution:**
1. Get your exact Vercel URL (e.g., `https://bot-trader-abc123.vercel.app`)
2. Add it to backend's `CORS_ALLOW_ORIGINS`
3. Restart backend

### "Network error" or "Failed to fetch"?
**Problem:** Frontend can't reach backend

**Solution:**
1. Check `NEXT_PUBLIC_API_URL` is set correctly in Vercel
2. Verify backend is running and accessible
3. Test backend URL directly: `curl https://your-backend.com/`

### Works locally but not on Vercel?
**Problem:** Environment variables not set in Vercel

**Solution:**
1. Go to Vercel Dashboard → Project Settings → Environment Variables
2. Add `NEXT_PUBLIC_API_URL` with your backend URL
3. Redeploy (Vercel will rebuild)

## Quick Checklist

Before deploying:
- [ ] Backend is deployed and accessible
- [ ] Backend URL works (test with curl or browser)
- [ ] Backend CORS includes your Vercel URL
- [ ] Frontend has `NEXT_PUBLIC_API_URL` set in Vercel
- [ ] Both use HTTPS (important for security)

## Local vs Production

### Local Development:
```typescript
// Frontend connects to localhost
API_URL = "http://127.0.0.1:8000"

// Backend allows localhost
CORS_ALLOW_ORIGINS = "http://localhost:3000"
```

### Production (Vercel):
```typescript
// Frontend connects to your backend server
API_URL = "https://your-backend.onrender.com"

// Backend allows Vercel URL
CORS_ALLOW_ORIGINS = "https://your-app.vercel.app"
```

## Pro Tips

1. **Use different env vars for dev/prod:**
   - Local: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
   - Production: `NEXT_PUBLIC_API_URL=https://your-backend.com`

2. **Test backend URL first:**
   ```bash
   curl https://your-backend.com/
   # Should return: {"message": "Welcome to the Trading SaaS API"}
   ```

3. **Check CORS in browser console:**
   - If you see CORS error, the backend needs your Vercel URL added

4. **Use environment-specific configs:**
   - Vercel supports different env vars for Preview vs Production

## Summary

**Frontend (Vercel):**
- Sets `NEXT_PUBLIC_API_URL` environment variable
- Makes API calls to that URL

**Backend (Your server):**
- Sets `CORS_ALLOW_ORIGINS` to include Vercel URL
- Allows requests from that origin

Both must match! Frontend calls backend, backend allows frontend.

