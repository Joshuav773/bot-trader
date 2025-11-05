#!/bin/bash
# Quick script to start backend locally

cd "$(dirname "$0")/.." || exit
source .venv/bin/activate 2>/dev/null || echo "⚠ Virtual environment not found. Activate manually: source .venv/bin/activate"
echo "Starting backend on http://127.0.0.1:8000"
echo "Press Ctrl+C to stop"
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
