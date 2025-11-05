#!/bin/bash
# Quick script to start backend locally

cd /Users/pending.../bot-trader
source .venv/bin/activate
echo "Starting backend on http://127.0.0.1:8000"
echo "Press Ctrl+C to stop"
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

