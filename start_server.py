#!/usr/bin/env python3
"""
Server startup script for Render deployment.
Handles port binding and ensures server starts correctly.
"""
import os
import sys
import warnings

# Suppress matplotlib warnings during font cache building
warnings.filterwarnings("ignore", message=".*font cache.*")
os.environ["MPLBACKEND"] = "Agg"  # Use non-interactive backend

# Get port from environment FIRST (Render sets this)
PORT = os.environ.get("PORT")
if not PORT:
    PORT = "8000"
    print(f"⚠ Warning: PORT environment variable not set, using default {PORT}")
else:
    print(f"✓ Found PORT environment variable: {PORT}")

port = int(PORT)

# Always use 0.0.0.0 by default (works for containers and local dev)
# Only use 127.0.0.1 if explicitly set in HOST environment variable
host = os.environ.get("HOST", "0.0.0.0")

# Determine if we're in development (reload mode)
# Only enable reload in true local development with explicit ENV=development
is_dev = os.environ.get("ENV", "").lower() == "development" and host == "127.0.0.1"
reload_enabled = is_dev

print(f"✓ Binding to {host}:{port}")
if "FLY_APP_NAME" in os.environ:
    print(f"✓ Detected Fly.io deployment: {os.environ.get('FLY_APP_NAME')}")

if __name__ == "__main__":
    print(f"🚀 Starting server on {host}:{port}")
    print(f"   Environment: {os.environ.get('ENV', 'production')}")
    print(f"   PORT env var: {os.environ.get('PORT', 'NOT SET')}")
    print(f"   HOST: {host}")
    if "FLY_APP_NAME" in os.environ:
        print(f"   Fly.io App: {os.environ.get('FLY_APP_NAME')}")
    if reload_enabled:
        print("   Development mode: Auto-reload enabled")
    
    try:
        import uvicorn
        # Start the server - this will bind to the port immediately
        # Use workers=1 for Fly.io to avoid issues
        # Prepare uvicorn arguments
        # Use uvicorn.run directly - don't use workers on Fly.io
        # Workers can cause issues with health checks and port binding
        print(f"✓ Starting uvicorn server...")
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            log_level="info",
            reload=reload_enabled,
            access_log=True,
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

