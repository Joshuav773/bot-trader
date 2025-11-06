# Deploy to Fly.io (Fastest Alternative)

Fly.io is **often the fastest** free option with global edge deployment and very fast builds.

## Why Fly.io?

✅ **Fastest builds** (1-3 minutes typically)  
✅ **Global edge deployment** (low latency worldwide)  
✅ **3 free VMs** (256MB each)  
✅ **160GB free outbound data**  
✅ **No forced sleep** (better than Render)  
✅ **Docker-based** (uses your Dockerfile)  

## Quick Deploy Steps

### 1. Install Fly CLI

**macOS:**
```bash
curl -L https://fly.io/install.sh | sh
```

**Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

**Windows:**
Download from https://fly.io/docs/getting-started/installing-flyctl/

### 2. Login to Fly.io

```bash
fly auth login
```

### 3. Initialize App (if needed)

If `fly.toml` doesn't exist or needs updating:

```bash
fly launch
```

This will:
- Detect your Dockerfile
- Ask for app name (or use existing `bot-trader-api`)
- Set up regions

### 4. Update Dockerfile

Make sure it uses `start_server.py`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "start_server.py"]
```

### 5. Set Secrets (Environment Variables)

```bash
fly secrets set POLYGON_API_KEY=your_key
fly secrets set DATABASE_URL=your_neon_connection_string
fly secrets set JWT_SECRET=random-secret-string
fly secrets set JWT_ALGORITHM=HS256
fly secrets set JWT_EXPIRES_MIN=60
fly secrets set CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
fly secrets set ADMIN_EMAIL=admin@example.com
fly secrets set ADMIN_PASSWORD=YourPassword123
fly secrets set POLYGON_LIMIT_5M=30
fly secrets set POLYGON_LIMIT_15M=60
fly secrets set POLYGON_LIMIT_30M=90
fly secrets set POLYGON_LIMIT_1H=730
fly secrets set POLYGON_LIMIT_4H=730
fly secrets set POLYGON_LIMIT_1D=3650
```

### 6. Update fly.toml

Your existing `fly.toml` should work, but verify it looks like:

```toml
app = "bot-trader-api"
primary_region = "iad"  # or your preferred region

[build]

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

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

### 7. Deploy

```bash
fly deploy
```

This will:
1. Build Docker image
2. Push to Fly.io
3. Deploy to edge locations
4. Give you URL: `https://bot-trader-api.fly.dev`

### 8. Update Frontend

In Vercel, update `NEXT_PUBLIC_API_URL`:
```
https://bot-trader-api.fly.dev
```

## Expected Performance

| Metric | Fly.io | Render | Railway |
|--------|--------|--------|---------|
| **Build Time** | 1-3 min | 5-8 min | 2-4 min |
| **Cold Start** | 5-10 sec | 30-60 sec | 10-20 sec |
| **Deploy Time** | 2-4 min | 6-10 min | 3-5 min |
| **Global Latency** | ✅ Best | ❌ Single region | ❌ Single region |

## Free Tier Limits

- **3 shared-cpu-1x VMs** (256MB RAM each)
- **160GB outbound data/month**
- **Auto-sleep** after inactivity (but very fast wake-up)
- **Global edge deployment** (free!)

## Useful Commands

```bash
# View logs
fly logs

# Check status
fly status

# Open app
fly open

# Scale up (if needed)
fly scale count 1

# View secrets
fly secrets list
```

## Troubleshooting

### Build Fails
```bash
fly logs  # Check build logs
```

### Port Issues
- Fly.io sets `PORT` automatically
- `start_server.py` already handles this

### Database Connection
- Use Neon PostgreSQL (same setup)
- Verify `DATABASE_URL` secret is set correctly

### Memory Issues
If you get OOM (out of memory) errors:
```bash
fly scale vm shared-cpu-1x  # Use smallest VM
# Or upgrade to paid plan for more RAM
```

## Upgrade Options

If you need more:
- **Paid VMs**: More RAM, better performance
- **Multiple regions**: Deploy globally
- **Always-on**: No auto-sleep

## Comparison Summary

| Platform | Build Speed | Free Tier | Ease of Use | Best For |
|----------|-------------|-----------|-------------|----------|
| **Fly.io** | ⚡ Fastest | ⭐⭐⭐ Good | ⚠️ CLI required | Fastest deploys |
| **Railway** | ⚡ Fast | ⭐⭐⭐⭐ Great | ✅ Web UI | Easiest |
| **Render** | 🐌 Slow | ⭐⭐ Limited | ✅ Web UI | Current setup |

## Recommendation

**For fastest deployments**: Use **Fly.io** (1-3 min builds)  
**For easiest setup**: Use **Railway** (2-4 min builds, web UI)

Both are faster than Render!

