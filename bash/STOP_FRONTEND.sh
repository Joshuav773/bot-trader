#!/bin/bash
# Stop frontend server running on port 3000

echo "Stopping frontend server on port 3000..."

# Find and kill process on port 3000
PID=$(lsof -ti :3000 2>/dev/null)

if [ -z "$PID" ]; then
    echo "✓ No frontend process found on port 3000"
else
    kill $PID 2>/dev/null
    echo "✓ Frontend stopped (PID: $PID)"
fi

