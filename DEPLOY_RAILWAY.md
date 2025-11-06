# Deploy to Railway (Faster Alternative)

Railway is often **2-3x faster** than Render for deployments and has a generous free tier.

## Why Railway?

✅ **Faster builds** (2-4 minutes vs 5-8 minutes on Render)  
✅ **500 hours/month free** (usually enough for small projects)  
✅ **Docker support** (uses your existing Dockerfile)  
✅ **Auto-deploy from GitHub**  
✅ **Better free tier** (no forced sleep after 15 min)  

## Quick Deploy Steps

### 1. Push Code to GitHub

```bash
git add .
git commit -m "Ready for Railway deployment"
git push
```

### 2. Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub (free)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `bot-trader` repository

### 3. Configure Service

Railway will auto-detect your Dockerfile. If not:

1. Click on your service
2. Go to "Settings" → "Generate Dockerfile" (or use existing)
3. Set **Start Command** (if not using Dockerfile):
   ```
   python start_server.py
   ```

### 4. Add Environment Variables

Go to "Variables" tab and add:

```bash
POLYGON_API_KEY=your_key
DATABASE_URL=your_neon_connection_string
JWT_SECRET=random-secret-string
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourPassword123
POLYGON_LIMIT_5M=30
POLYGON_LIMIT_15M=60
POLYGON_LIMIT_30M=90
POLYGON_LIMIT_1H=730
POLYGON_LIMIT_4H=730
POLYGON_LIMIT_1D=3650
PORT=8000  # Railway sets this automatically, but good to have
```

### 5. Update Dockerfile (if needed)

Railway prefers using the Dockerfile. Update it to use `start_server.py`:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Use our startup script
CMD ["python", "start_server.py"]
```

### 6. Deploy

Railway will automatically:
1. Build from Dockerfile
2. Deploy your service
3. Give you a URL like: `https://bot-trader-api.up.railway.app`

### 7. Update Frontend

In Vercel, update `NEXT_PUBLIC_API_URL`:
```
https://bot-trader-api.up.railway.app
```

## Expected Performance

| Metric | Railway | Render |
|--------|---------|--------|
| **Build Time** | 2-4 min | 5-8 min |
| **Cold Start** | 10-20 sec | 30-60 sec |
| **Deploy Time** | 3-5 min | 6-10 min |

## Troubleshooting

### Port Issues
- Railway sets `PORT` automatically
- Make sure `start_server.py` reads `PORT` env var (already done)

### Build Fails
- Check Railway logs: Service → "Deployments" → Click latest
- Verify Dockerfile is in root directory
- Check that `requirements.txt` is valid

### Database Connection
- Use Neon PostgreSQL (same as Render setup)
- Verify `DATABASE_URL` is correct in Railway variables

## Free Tier Limits

- **500 hours/month** compute time
- **$5 credit** (enough for small projects)
- **Auto-sleep** after inactivity (but faster wake-up than Render)

## Upgrade Options

If you need more:
- **Hobby Plan** ($5/month): Always-on, no sleep
- **Pro Plan** ($20/month): More resources, priority support

