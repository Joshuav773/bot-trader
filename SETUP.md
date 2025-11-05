# Setup Guide

## First Time Setup

### 1. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Create `.env` File

Create `.env` in project root:

```bash
# API Keys
POLYGON_API_KEY=your_polygon_key_here
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here

# Database (SQLite for local, or use Neon PostgreSQL)
DATABASE_URL=sqlite:///./app.db

# JWT Settings
JWT_SECRET=change-me-to-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60

# CORS - Allow local frontend
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Admin User
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourPassword123

# Polygon Data Limits (days)
POLYGON_LIMIT_5M=30
POLYGON_LIMIT_15M=60
POLYGON_LIMIT_30M=90
POLYGON_LIMIT_1H=730
POLYGON_LIMIT_4H=730
POLYGON_LIMIT_1D=3650
```

### 4. Start Backend

**Terminal 1:**
```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Start Frontend

**Terminal 2:**
```bash
cd frontend
npm run dev
```

### 6. Access Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://127.0.0.1:8000/docs
- **Login**: Use `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`

## Quick Start Scripts

Use the provided shell scripts in the `bash/` directory:

```bash
# Start Backend
./bash/START_LOCAL.sh

# Start Frontend (in another terminal)
./bash/START_FRONTEND.sh

# Stop Backend
./bash/STOP_BACKEND.sh

# Stop Frontend
./bash/STOP_FRONTEND.sh
```

## Troubleshooting

### Backend Issues
- **Port 8000 in use**: `lsof -i :8000` then kill process
- **Missing dependencies**: `pip install -r requirements.txt`
- **Database errors**: Check `DATABASE_URL` in `.env`

### Frontend Issues
- **Build errors**: `npm install` in frontend directory
- **TypeScript errors**: Already fixed in codebase
- **Port 3000 in use**: `lsof -i :3000` then kill process

### Login Issues
- Check backend is running
- Verify `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`
- Check backend logs for errors

