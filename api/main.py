import os
import warnings

# Suppress matplotlib warnings during font cache building (happens on first import)
warnings.filterwarnings("ignore", message=".*font cache.*")
os.environ["MPLBACKEND"] = "Agg"  # Use non-interactive backend to avoid GUI issues

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.routers import analysis as analysis_router
from api.routers import backtest as backtest_router
from api.routers import ml as ml_router
from api.routers import auth as auth_router
from api.routers import models as models_router
from api.routers import orderflow as orderflow_router
from api.routers import confluence as confluence_router
from api.routers import news as news_router
from api.routers import forex as forex_router
from api.security import get_current_user
from api.db import create_db_and_tables
from api.bootstrap import ensure_single_admin_user
from config.settings import CORS_ALLOW_ORIGINS

app = FastAPI(title="Trading SaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Startup event - runs after server starts (non-blocking)"""
    import asyncio
    import sys
    
    # Log that server is ready
    print("=" * 50)
    print("✅ FastAPI server is ready and listening!")
    print(f"   Health endpoint ready at /health")
    print("=" * 50)
    sys.stdout.flush()  # Ensure logs are flushed immediately
    
    async def init_db():
        """Initialize database in background"""
        try:
            print("🔄 Initializing database...")
            # Run in executor to avoid blocking startup
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, create_db_and_tables)
            print("✓ Database initialized")
            
            print("🔄 Ensuring admin user...")
            await loop.run_in_executor(None, ensure_single_admin_user)
            print("✓ Admin user ready")
        except Exception as e:
            print(f"⚠ Warning during startup: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail startup if these fail - server can still run
    
    # Run DB init in background so server can start immediately
    asyncio.create_task(init_db())


app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(backtest_router.router, prefix="/backtest", tags=["backtest"], dependencies=[Depends(get_current_user)])
app.include_router(analysis_router.router, prefix="/analysis", tags=["analysis"], dependencies=[Depends(get_current_user)])
app.include_router(ml_router.router, prefix="/ml", tags=["ml"], dependencies=[Depends(get_current_user)])
app.include_router(models_router.router, tags=["models"], dependencies=[Depends(get_current_user)])
app.include_router(orderflow_router.router, prefix="/order-flow", tags=["order-flow"], dependencies=[Depends(get_current_user)])
app.include_router(confluence_router.router, prefix="/confluence", tags=["confluence"], dependencies=[Depends(get_current_user)])
app.include_router(news_router.router, prefix="/news", tags=["news"], dependencies=[Depends(get_current_user)])
app.include_router(forex_router.router, prefix="/forex", tags=["forex"], dependencies=[Depends(get_current_user)])


@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading SaaS API"}


@app.get("/health")
def health_check():
    """Health check endpoint for Fly.io, Render and monitoring - responds immediately"""
    # Always return healthy - don't check DB to avoid blocking
    # Server can start even if DB connection fails initially
    return {"status": "healthy", "service": "bot-trader-api"}


