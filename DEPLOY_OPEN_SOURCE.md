# Open Source Backend Deployment Guide

This guide covers deployment options that are open source and give you full control over URLs, CORS, and database connections.

## Option 1: Docker Compose (Recommended - Full Control)

**Best for**: Self-hosting with complete control, easy configuration changes

### Quick Start

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** - Easy configuration:
   ```bash
   # Change CORS origins
   CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
   
   # Change database (or use included Postgres)
   DATABASE_URL=postgresql+psycopg://user:pass@host/db
   
   # Set your API keys
   POLYGON_API_KEY=your_key
   
   # Admin credentials
   ADMIN_EMAIL=admin@yourdomain.com
   ADMIN_PASSWORD=YourPassword
   ```

3. **Start everything**:
   ```bash
   docker-compose up -d
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f backend
   ```

### Benefits:
- ✅ **Full Control**: Change URLs, CORS, configs instantly
- ✅ **Database Included**: PostgreSQL runs in container
- ✅ **Easy Updates**: Just edit `.env` and restart
- ✅ **Open Source**: All Docker Compose files
- ✅ **Portable**: Run on any server (VPS, cloud, etc.)

### Changing Configuration:

**Update CORS**:
```bash
# Edit .env
CORS_ALLOW_ORIGINS=https://new-frontend.com,https://another-app.com

# Restart
docker-compose restart backend
```

**Update Database**:
```bash
# Edit .env - change DATABASE_URL
DATABASE_URL=postgresql+psycopg://newuser:pass@newhost/db

# Restart
docker-compose restart backend
```

**Update Admin Credentials**:
```bash
# Edit .env
ADMIN_EMAIL=newadmin@example.com
ADMIN_PASSWORD=NewPassword123

# Restart (will recreate admin user)
docker-compose restart backend
```

### Access Points:
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432

### Deploy to VPS/Cloud:

1. **Copy files to server** (via git, scp, etc.)
2. **Set environment variables** in `.env`
3. **Run**: `docker-compose up -d`
4. **Set up reverse proxy** (nginx/caddy) for HTTPS

---

## Option 2: Fly.io (Open Source Platform)

**Best for**: Managed hosting with easy config changes

### Setup

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Launch app**:
   ```bash
   fly launch
   ```

4. **Set secrets** (environment variables):
   ```bash
   # Set all your configs
   fly secrets set POLYGON_API_KEY=your_key
   fly secrets set DATABASE_URL=your_neon_url
   fly secrets set CORS_ALLOW_ORIGINS=https://your-frontend.vercel.app
   fly secrets set ADMIN_EMAIL=admin@example.com
   fly secrets set ADMIN_PASSWORD=YourPassword
   ```

5. **Deploy**:
   ```bash
   fly deploy
   ```

### Benefits:
- ✅ **Open Source Platform**: Fly.io is open source
- ✅ **Easy Config**: `fly secrets set` for any changes
- ✅ **Global CDN**: Fast worldwide
- ✅ **Free Tier**: 3 shared VMs free

### Update Configuration:
```bash
# Change CORS
fly secrets set CORS_ALLOW_ORIGINS=https://new-frontend.com

# Redeploy
fly deploy
```

---

## Option 3: Self-Hosted with Systemd (Full Control)

**Best for**: Production servers with systemd

### Setup

1. **Install dependencies on server**:
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv postgresql nginx
   ```

2. **Create systemd service** (`/etc/systemd/system/bot-trader-api.service`):
   ```ini
   [Unit]
   Description=Bot Trader API
   After=network.target postgresql.service

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/bot-trader
   Environment="PATH=/opt/bot-trader/.venv/bin"
   ExecStart=/opt/bot-trader/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. **Edit environment**: `/opt/bot-trader/.env`

4. **Start service**:
   ```bash
   sudo systemctl enable bot-trader-api
   sudo systemctl start bot-trader-api
   ```

### Benefits:
- ✅ **Full Control**: Direct access to all configs
- ✅ **System Integration**: Works with systemd, nginx, etc.
- ✅ **Production Ready**: Standard Linux deployment

---

## Database Options

### Option A: Docker Compose PostgreSQL (Included)
- Already configured in `docker-compose.yml`
- Automatic setup, no external service needed
- Data persists in Docker volume

### Option B: Neon (External PostgreSQL)
- Free tier available
- Managed database
- Change `DATABASE_URL` in `.env`

### Option C: Self-Hosted PostgreSQL
- Install on your server
- Full control
- Update `DATABASE_URL` in `.env`

---

## Configuration File Reference

All configuration is in `.env` file:

```bash
# Easy to change URLs
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-app.vercel.app

# Easy database switching
DATABASE_URL=postgresql+psycopg://user:pass@host/db

# Easy admin setup
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=YourPassword

# Easy API key updates
POLYGON_API_KEY=your_key
```

**To apply changes**: Restart the service (Docker Compose: `docker-compose restart backend`)

---

## Recommended: Docker Compose Setup

For maximum flexibility and easy configuration:

1. **Use Docker Compose** (includes database)
2. **Deploy to any VPS** (DigitalOcean, Linode, Hetzner, etc.)
3. **Easy config changes** via `.env` file
4. **Full control** over URLs, CORS, database

### Quick Deploy to VPS:

```bash
# On your server
git clone your-repo
cd bot-trader
cp .env.example .env
# Edit .env with your settings
docker-compose up -d
```

That's it! Your backend is running with full control.

---

## Need Help?

- **Docker Compose**: See `docker-compose.yml` and `.env.example`
- **Configuration**: All in `config/settings.py` (reads from `.env`)
- **CORS**: Set in `CORS_ALLOW_ORIGINS` environment variable
- **Database**: Set in `DATABASE_URL` environment variable

