#!/bin/bash
# Quick script to start frontend locally

cd "$(dirname "$0")/../frontend" || exit
echo "Starting frontend on http://localhost:3000"
echo "Press Ctrl+C to stop"
npm run dev
