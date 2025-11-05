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

import uvicorn

# Get port from environment (Render sets this)
port = int(os.environ.get("PORT", 8000))
host = os.environ.get("HOST", "0.0.0.0")

if __name__ == "__main__":
    print(f"Starting server on {host}:{port}")
    # Start the server
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        log_level="info",
    )

