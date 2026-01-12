#!/usr/bin/env python3
"""
Extract token.json content for AWS deployment.
This formats the token JSON as a single-line string for environment variable.
"""
import json
import sys
from pathlib import Path

TOKEN_FILE = Path("token.json")

if not TOKEN_FILE.exists():
    print("❌ Error: token.json not found!")
    print("Please run 'python3 schwab_streamer.py' locally first to create token.json")
    sys.exit(1)

try:
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
    
    # Convert to single-line JSON string
    token_json = json.dumps(token_data)
    
    print("📋 SCHWAB_TOKEN_JSON for AWS deployment:")
    print("")
    print("Copy this value and set it as an environment variable on your AWS instance:")
    print("")
    print(f"SCHWAB_TOKEN_JSON='{token_json}'")
    print("")
    print("Or add it to your .env file on AWS:")
    print(f"SCHWAB_TOKEN_JSON={token_json}")
    print("")
    print("⚠️  Note: Keep this token secure! It provides full API access.")
    
except Exception as e:
    print(f"❌ Error reading token.json: {e}")
    sys.exit(1)


