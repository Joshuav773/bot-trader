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
host = os.environ.get("HOST", "0.0.0.0")

# For Render, always use 0.0.0.0 to bind to all interfaces
# Render sets RENDER=true in environment
if "RENDER" in os.environ or os.environ.get("ENV") == "production":
    host = "0.0.0.0"
    print(f"✓ Production mode: Binding to {host}")

# Determine if we're in development (reload mode)
is_dev = os.environ.get("ENV", "").lower() != "production"
reload_enabled = is_dev and host == "127.0.0.1"

if __name__ == "__main__":
    print(f"🚀 Starting server on {host}:{port}")
    print(f"   Environment: {os.environ.get('ENV', 'production')}")
    print(f"   PORT env var: {os.environ.get('PORT', 'NOT SET')}")
    if reload_enabled:
        print("   Development mode: Auto-reload enabled")
    
    try:
        import uvicorn
        # Start the server - this will bind to the port immediately
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

