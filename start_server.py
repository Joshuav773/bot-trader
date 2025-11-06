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
    
    # Flush output immediately
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        import uvicorn
        import signal
        import atexit
        
        # Register cleanup handlers
        def cleanup():
            print("\n🛑 Server shutting down...")
            sys.stdout.flush()
        
        atexit.register(cleanup)
        
        def signal_handler(sig, frame):
            print(f"\n🛑 Received signal {sig}, shutting down gracefully...")
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        print(f"✓ Starting uvicorn server on {host}:{port}")
        print(f"   Server will bind immediately - ML libraries load in background")
        sys.stdout.flush()
        
        # Use uvicorn.run() - it will import the app and bind
        # The health endpoint is registered first in api/main.py, so it should respond quickly
        # even while TensorFlow loads in the background
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
        sys.stdout.flush()
        sys.exit(0)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        sys.exit(1)

