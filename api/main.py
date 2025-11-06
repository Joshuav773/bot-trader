import os
import warnings

# Suppress matplotlib warnings during font cache building (happens on first import)
warnings.filterwarnings("ignore", message=".*font cache.*")
os.environ["MPLBACKEND"] = "Agg"  # Use non-interactive backend to avoid GUI issues

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

# Create app FIRST - this allows health endpoint to be registered immediately
app = FastAPI(title="Trading SaaS API")

# IMPORTANT: CORS middleware must be added BEFORE registering routes
# We'll add it after imports, but we need to ensure it's early

# Health endpoint - register IMMEDIATELY before any expensive imports
# This ensures Fly.io health checks work even while ML libraries are loading
@app.get("/health")
@app.get("/healthz")
@app.get("/health/")
def health_check():
    """Health check endpoint - responds immediately, even during startup"""
    # This endpoint should NEVER import anything expensive
    # It's called by Fly.io health checks during startup
    return {"status": "healthy", "service": "bot-trader-api"}

# Import routers with error handling - don't crash if one fails to import
# This allows the app to start even if some routers have issues
_routers_loaded = {}
try:
    from api.routers import analysis as analysis_router
    _routers_loaded['analysis'] = analysis_router
except Exception as e:
    print(f"⚠ Warning: Failed to import analysis router: {e}")
    analysis_router = None

try:
    from api.routers import backtest as backtest_router
    _routers_loaded['backtest'] = backtest_router
except Exception as e:
    print(f"⚠ Warning: Failed to import backtest router: {e}")
    backtest_router = None

try:
    from api.routers import ml as ml_router
    _routers_loaded['ml'] = ml_router
except Exception as e:
    print(f"⚠ Warning: Failed to import ml router: {e}")
    ml_router = None

try:
    from api.routers import auth as auth_router
    _routers_loaded['auth'] = auth_router
except Exception as e:
    print(f"⚠ Warning: Failed to import auth router: {e}")
    auth_router = None

try:
    from api.routers import models as models_router
    _routers_loaded['models'] = models_router
except Exception as e:
    print(f"⚠ Warning: Failed to import models router: {e}")
    models_router = None

try:
    from api.routers import orderflow as orderflow_router
    _routers_loaded['orderflow'] = orderflow_router
except Exception as e:
    print(f"⚠ Warning: Failed to import orderflow router: {e}")
    orderflow_router = None

try:
    from api.routers import confluence as confluence_router
    _routers_loaded['confluence'] = confluence_router
except Exception as e:
    print(f"⚠ Warning: Failed to import confluence router: {e}")
    confluence_router = None

try:
    from api.routers import news as news_router
    _routers_loaded['news'] = news_router
except Exception as e:
    print(f"⚠ Warning: Failed to import news router: {e}")
    news_router = None

try:
    from api.routers import forex as forex_router
    _routers_loaded['forex'] = forex_router
except Exception as e:
    print(f"⚠ Warning: Failed to import forex router: {e}")
    forex_router = None

try:
    from api.security import get_current_user
    from api.db import create_db_and_tables
    from api.bootstrap import ensure_single_admin_user
    from config.settings import CORS_ALLOW_ORIGINS
    print(f"✓ Core modules imported successfully")
    print(f"✓ Routers loaded: {list(_routers_loaded.keys())}")
except ImportError as e:
    print(f"❌ Critical import error: {e}")
    import traceback
    traceback.print_exc()
    raise

# Add request logging middleware to debug CORS issues
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging CORS issues"""
    origin = request.headers.get("origin", "None")
    method = request.method
    path = request.url.path
    print(f"📥 {method} {path} | Origin: {origin}")
    
    response = await call_next(request)
    
    # Log CORS headers in response
    cors_headers = {
        k: v for k, v in response.headers.items() 
        if k.lower().startswith("access-control")
    }
    if cors_headers:
        print(f"   ✓ CORS headers: {cors_headers}")
    elif method == "OPTIONS":
        print(f"   ⚠️  No CORS headers in OPTIONS response!")
    
    return response

# Add CORS middleware with error handling
# This MUST be added before any routes to handle preflight requests
try:
    print(f"🔧 Configuring CORS with origins: {CORS_ALLOW_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,  # List of allowed origins
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],  # Explicit methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"],  # Expose all headers
        max_age=3600,  # Cache preflight for 1 hour
    )
    print(f"✓ CORS middleware configured with {len(CORS_ALLOW_ORIGINS)} allowed origin(s)")
    print(f"   Allowed origins: {', '.join(CORS_ALLOW_ORIGINS)}")
except Exception as e:
    print(f"⚠ Warning: Failed to configure CORS middleware: {e}")
    # App will still work, just without CORS (might cause issues with frontend)
    import traceback
    traceback.print_exc()

# Explicit OPTIONS handler - MUST be registered BEFORE other routes
# FastAPI processes routes in order, so this catch-all needs to be first
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Handle OPTIONS preflight requests explicitly - catch-all for all routes"""
    origin = request.headers.get("origin", "")
    print(f"🔍 OPTIONS request from origin: '{origin}', path: '{full_path}'")
    print(f"   Allowed origins: {CORS_ALLOW_ORIGINS}")
    
    # Check if origin is allowed (case-sensitive match)
    if origin in CORS_ALLOW_ORIGINS:
        print(f"✓ Allowing OPTIONS from {origin}")
        response = Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "3600",
            },
        )
        return response
    else:
        print(f"⚠ Rejecting OPTIONS from '{origin}' (not in allowed origins)")
        # Still return CORS headers but with 403 - browser will see the headers
        return Response(
            status_code=403,
            headers={
                "Access-Control-Allow-Origin": origin if origin else "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            },
        )


@app.on_event("startup")
async def on_startup():
    """Startup event - runs after server starts (non-blocking)"""
    import asyncio
    import sys
    
    # Log that server is ready
    port = os.environ.get("PORT", "8000")
    print("=" * 50)
    print("✅ FastAPI server is ready and listening!")
    print(f"   Health endpoint ready at /health")
    print(f"   Expected to be listening on 0.0.0.0:{port}")
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


# Include routers only if they loaded successfully
if auth_router:
    app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
if backtest_router:
    app.include_router(backtest_router.router, prefix="/backtest", tags=["backtest"], dependencies=[Depends(get_current_user)])
if analysis_router:
    app.include_router(analysis_router.router, prefix="/analysis", tags=["analysis"], dependencies=[Depends(get_current_user)])
if ml_router:
    app.include_router(ml_router.router, prefix="/ml", tags=["ml"], dependencies=[Depends(get_current_user)])
if models_router:
    app.include_router(models_router.router, tags=["models"], dependencies=[Depends(get_current_user)])
if orderflow_router:
    app.include_router(orderflow_router.router, prefix="/order-flow", tags=["order-flow"], dependencies=[Depends(get_current_user)])
if confluence_router:
    app.include_router(confluence_router.router, prefix="/confluence", tags=["confluence"], dependencies=[Depends(get_current_user)])
if news_router:
    app.include_router(news_router.router, prefix="/news", tags=["news"], dependencies=[Depends(get_current_user)])
if forex_router:
    app.include_router(forex_router.router, prefix="/forex", tags=["forex"], dependencies=[Depends(get_current_user)])


@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading SaaS API"}
