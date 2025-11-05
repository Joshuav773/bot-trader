# Environment Variables: Local vs Render

## Local `.env` File (For Testing on Your Computer)

Create this file in your project root: `/Users/pending.../bot-trader/.env`

```bash
# API Keys
POLYGON_API_KEY=your_polygon_key_here
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here

# Database - For local testing, you can use SQLite
DATABASE_URL=sqlite:///./app.db

# OR use your Neon database (same as Render)
# DATABASE_URL=postgresql+psycopg://user:pass@host.neon.tech/dbname?sslmode=require

# JWT Settings
JWT_SECRET=change-me-to-random-secret-12345
JWT_ALGORITHM=HS256
JWT_EXPIRES_MIN=60

# CORS - Allow local frontend
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Admin User
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=YourSecurePassword123

# Polygon Data Limits
POLYGON_LIMIT_5M=30
POLYGON_LIMIT_15M=60
POLYGON_LIMIT_30M=90
POLYGON_LIMIT_1H=730
POLYGON_LIMIT_4H=730
POLYGON_LIMIT_1D=3650
```

**Key differences:**
- `DATABASE_URL` can be SQLite for local (easier) or same Neon DB
- `CORS_ALLOW_ORIGINS` includes `localhost:3000` for local frontend
- No `$` signs (those are just Render's UI indicators)

---

## Render Environment Variables (For Deployed Backend)

In Render dashboard → Your Service → Environment tab:

```
POLYGON_API_KEY = your_polygon_key_here
DATABASE_URL = postgresql+psycopg://user:pass@host.neon.tech/dbname?sslmode=require
JWT_SECRET = random-secret-string-12345
JWT_ALGORITHM = HS256
JWT_EXPIRES_MIN = 60
CORS_ALLOW_ORIGINS = http://localhost:3000,https://your-vercel-app.vercel.app
ADMIN_EMAIL = admin@example.com
ADMIN_PASSWORD = YourSecurePassword123
POLYGON_LIMIT_5M = 30
POLYGON_LIMIT_15M = 60
POLYGON_LIMIT_30M = 90
POLYGON_LIMIT_1H = 730
POLYGON_LIMIT_4H = 730
POLYGON_LIMIT_1D = 3650
```

**Key differences:**
- `DATABASE_URL` must be PostgreSQL (from Neon)
- `CORS_ALLOW_ORIGINS` includes your Vercel frontend URL
- No quotes needed in Render (just paste the values)

---

## Quick Setup

### For Local Testing:

1. Create `.env` file in project root
2. Copy the local version above
3. Fill in your actual API keys
4. Use SQLite for database (simpler) or Neon if you want to test with same DB

### For Render Deployment:

1. Get Neon database connection string
2. Add all variables in Render dashboard
3. Make sure `CORS_ALLOW_ORIGINS` includes your Vercel URL (add this after you deploy frontend)

---

## Important Notes

- **Never commit `.env` to GitHub** (it's in `.gitignore`)
- **Render variables are separate** - set them in Render dashboard
- **Same values, different places** - local `.env` for local testing, Render for production

