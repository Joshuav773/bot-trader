#!/usr/bin/env bash
set -e

PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ_DIR"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

source venv/bin/activate

echo "Starting backend on :8765 ..."
uvicorn agent_chat.main:app --reload --host 0.0.0.0 --port 8765 &
BACKEND_PID=$!

echo "Starting frontend on :3000 ..."
cd agent_chat_ui && npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend  → http://localhost:8765"
echo "  Frontend → http://localhost:3000  (use this for dev)"
echo ""
echo "  Press Ctrl+C to stop both."
echo ""

wait
