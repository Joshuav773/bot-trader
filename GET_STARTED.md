# Getting Started - Step by Step Guide

## Step 1: Get the UI Running Locally First

Before using Docker Compose, let's make sure everything works locally.

### A. Install Frontend Dependencies

```bash
cd frontend
npm install
```

This installs Next.js, React, Plotly, and other dependencies.

### B. Start the Backend (Terminal 1)

```bash
# From project root
source .venv/bin/activate  # Activate Python virtual environment
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### C. Start the Frontend (Terminal 2)

```bash
# From frontend directory
cd frontend
npm run dev
```

You should see:
```
✓ Ready in 2.3s
○ Local:        http://localhost:3000
```

### D. Access the UI

1. Open browser: http://localhost:3000
2. Login with credentials from your `.env` file:
   - Email: `ADMIN_EMAIL`
   - Password: `ADMIN_PASSWORD`

### E. Test It Works

- Try logging in
- Go to Dashboard
- Try loading a chart (AAPL, 1d timeframe)
- Try running a backtest

---

## Step 2: Learn Docker Compose Basics

### What is Docker Compose?

Docker Compose lets you run multiple services (like your backend + database) together with one command.

### Key Concepts:

1. **Docker**: Packages your app in a container (like a virtual machine but lighter)
2. **Docker Compose**: Runs multiple containers together
3. **Services**: Each container is a "service" (backend, database, etc.)

### Our Setup:

- **Backend Service**: Your FastAPI app
- **Postgres Service**: Database (automatically included!)

---

## Step 3: Use Docker Compose

### A. Create Environment File

```bash
# From project root
cp .env.example .env
```

### B. Edit `.env` File

Open `.env` and set:
```bash
# API Keys (get from Polygon.io, Alpaca)
POLYGON_API_KEY=your_key_here
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here

# CORS - Add your frontend URL
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Admin credentials
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourPassword123

# Database (Docker Compose will use internal postgres)
# Or use external like Neon:
# DATABASE_URL=postgresql+psycopg://user:pass@host/db

# JWT Secret (generate a random string)
JWT_SECRET=your-random-secret-here
```

### C. Start Docker Compose

```bash
# From project root
docker-compose up -d
```

**What this does:**
- `up` = Start all services
- `-d` = Run in background (detached mode)

**First time:** It will:
1. Download PostgreSQL image (~100MB)
2. Build your backend Docker image
3. Start both services
4. Create database automatically
5. Run migrations

### D. Check Status

```bash
# See what's running
docker-compose ps

# See logs
docker-compose logs -f backend

# Stop everything
docker-compose down
```

### E. Access Your Services

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432 (user: postgres, password: postgres)

---

## Step 4: Run Frontend with Docker Backend

Now your backend runs in Docker, but frontend still runs locally:

```bash
# Terminal 1: Backend is already running in Docker
# (no need to start it separately)

# Terminal 2: Start frontend locally
cd frontend
npm run dev
```

The frontend will connect to `http://localhost:8000` (your Docker backend).

---

## Common Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a service
docker-compose restart backend

# See logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Rebuild after code changes
docker-compose up -d --build

# View running services
docker-compose ps

# Execute command in container
docker-compose exec backend python -m scripts.seed_admin
```

---

## Troubleshooting

### Backend won't start?
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing .env file
# - Wrong DATABASE_URL
# - Port 8000 already in use
```

### Database connection issues?
```bash
# Check if postgres is running
docker-compose ps

# Check postgres logs
docker-compose logs postgres

# Restart everything
docker-compose restart
```

### Changed code and need to rebuild?
```bash
docker-compose up -d --build
```

### Want to start fresh?
```bash
# Stop and remove everything (including data)
docker-compose down -v

# Start again
docker-compose up -d
```

---

## Next Steps

Once you're comfortable with Docker Compose locally:

1. **Deploy to VPS**: Copy files to server, run `docker-compose up -d`
2. **Add Nginx**: Reverse proxy for HTTPS
3. **Backup Database**: Set up automated backups

---

## Quick Reference

| Task | Command |
|------|---------|
| Start everything | `docker-compose up -d` |
| Stop everything | `docker-compose down` |
| View logs | `docker-compose logs -f backend` |
| Restart backend | `docker-compose restart backend` |
| Rebuild after changes | `docker-compose up -d --build` |
| Check status | `docker-compose ps` |

