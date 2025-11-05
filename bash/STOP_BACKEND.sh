#!/bin/bash
# Stop backend server running on port 8000

echo "Stopping backend server on port 8000..."

# Find and kill process on port 8000
PID=$(lsof -ti :8000 2>/dev/null)

if [ -z "$PID" ]; then
    echo "✓ No backend process found on port 8000"
else
    kill $PID 2>/dev/null
    echo "✓ Backend stopped (PID: $PID)"
fi

