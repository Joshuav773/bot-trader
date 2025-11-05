#!/bin/bash
# Quick script to start backend locally

cd "$(dirname "$0")/.." || exit
source .venv/bin/activate 2>/dev/null || echo "⚠ Virtual environment not found. Activate manually: source .venv/bin/activate"

# Set port and host for local development
export PORT=8000
export HOST=127.0.0.1
export ENV=development

echo "Starting backend on http://${HOST}:${PORT}"
echo "Development mode: Auto-reload enabled"
echo "Press Ctrl+C to stop"
python start_server.py
