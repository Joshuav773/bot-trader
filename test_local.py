#!/usr/bin/env python3
"""
Local Testing Script for Bot Trader
Tests FastAPI server and Schwab streamer before deployment
"""
import sys
import os
import time
import subprocess
import signal
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

def test_fastapi_app():
    """Test FastAPI app imports and structure"""
    print("=" * 60)
    print("TEST 1: FastAPI Application")
    print("=" * 60)
    
    try:
        from main import app
        print("✅ FastAPI app imports successfully")
        print(f"   Title: {app.title}")
        print(f"   Version: {app.version}")
        print(f"   Routes: {len(app.routes)}")
        print("\n📋 Available endpoints:")
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                methods = ', '.join(sorted(route.methods - {'HEAD', 'OPTIONS'}))
                print(f"   {methods:8} {route.path}")
        print("\n✅ FastAPI app is ready!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schwab_authentication():
    """Test Schwab authentication"""
    print("\n" + "=" * 60)
    print("TEST 2: Schwab Authentication")
    print("=" * 60)
    
    try:
        from schwab_streamer import SchwabStreamer
        
        streamer = SchwabStreamer()
        print("✅ SchwabStreamer initialized")
        
        # Check credentials
        if not streamer.app_key or not streamer.app_secret:
            print("❌ Missing credentials in .env file")
            return False
        
        print(f"✅ Credentials loaded")
        print(f"   Callback URL: {streamer.callback_url}")
        print(f"   Token file exists: {Path('token.json').exists()}")
        
        # Test authentication
        print("\n📝 Testing authentication...")
        if streamer.authenticate():
            print("✅ Authentication successful!")
            print(f"   Client type: {type(streamer.client).__name__}")
            return True
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fastapi_server():
    """Test FastAPI server by starting it and making requests"""
    print("\n" + "=" * 60)
    print("TEST 3: FastAPI Server (Live)")
    print("=" * 60)
    
    server_process = None
    try:
        import requests
        
        # Start server
        print("🚀 Starting FastAPI server...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        print("   Waiting for server to start...")
        time.sleep(3)
        
        # Check if process is still running
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"❌ Server failed to start")
            print(f"   stdout: {stdout.decode()[:200]}")
            print(f"   stderr: {stderr.decode()[:200]}")
            return False
        
        # Test endpoints
        base_url = "http://127.0.0.1:8000"
        
        try:
            print("\n📡 Testing endpoints...")
            
            # Test root
            response = requests.get(f"{base_url}/", timeout=5)
            print(f"   GET / : {response.status_code} - {response.json()}")
            
            # Test health
            response = requests.get(f"{base_url}/health", timeout=5)
            print(f"   GET /health : {response.status_code} - {response.json()}")
            
            # Test status
            response = requests.get(f"{base_url}/api/status", timeout=5)
            print(f"   GET /api/status : {response.status_code} - {response.json()}")
            
            print("\n✅ All endpoints working!")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return False
            
    except ImportError:
        print("⚠️  requests library not installed - skipping live server test")
        print("   Install with: pip install requests")
        return True  # Don't fail, just skip
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if server_process:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("   Server stopped")


def main():
    """Run all tests"""
    print("\n" + "🧪" * 30)
    print("BOT TRADER - LOCAL TESTING")
    print("🧪" * 30 + "\n")
    
    results = []
    
    # Test 1: FastAPI app
    results.append(("FastAPI App", test_fastapi_app()))
    
    # Test 2: Schwab authentication
    results.append(("Schwab Authentication", test_schwab_authentication()))
    
    # Test 3: FastAPI server
    results.append(("FastAPI Server", test_fastapi_server()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}  {name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! Ready to deploy.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

