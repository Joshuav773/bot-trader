"""
Startup script - Runs both FastAPI server and Schwab streamer
"""
import os
import sys
import subprocess
import signal
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get port from environment
PORT = os.environ.get("PORT", "8000")
HOST = os.environ.get("HOST", "0.0.0.0")

processes = []


def cleanup(signum=None, frame=None):
    """Cleanup function to stop all processes"""
    logger.info("\n🛑 Shutting down services...")
    for proc in processes:
        if proc.poll() is None:
            logger.info(f"   Stopping PID {proc.pid}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    logger.info("✅ All services stopped")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)


if __name__ == "__main__":
    logger.info("🚀 Starting Bot Trader Services")
    logger.info(f"   FastAPI Server: {HOST}:{PORT}")
    logger.info(f"   Schwab Streamer: Starting...")
    logger.info("")
    
    # Start FastAPI server
    logger.info("📡 Starting FastAPI server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", HOST, "--port", PORT],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(api_process)
    logger.info(f"   ✓ FastAPI server started (PID: {api_process.pid})")
    
    # Wait a moment for API to initialize
    time.sleep(2)
    
    # Start Schwab streamer
    logger.info("📊 Starting Schwab streamer...")
    streamer_process = subprocess.Popen(
        [sys.executable, "schwab_streamer.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(streamer_process)
    logger.info(f"   ✓ Schwab streamer started (PID: {streamer_process.pid})")
    logger.info("")
    logger.info("✅ All services running!")
    logger.info("   Press Ctrl+C to stop")
    logger.info("")
    
    # Monitor processes and restart if they crash
    try:
        while True:
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    service_name = "FastAPI server" if i == 0 else "Schwab streamer"
                    logger.warning(f"⚠️  {service_name} (PID: {proc.pid}) exited with code {proc.returncode}")
                    
                    if i == 0:
                        # Restart API
                        logger.info(f"   Restarting {service_name}...")
                        new_proc = subprocess.Popen(
                            [sys.executable, "-m", "uvicorn", "main:app", "--host", HOST, "--port", PORT],
                            stdout=sys.stdout,
                            stderr=sys.stderr
                        )
                    else:
                        # Restart streamer
                        logger.info(f"   Restarting {service_name}...")
                        new_proc = subprocess.Popen(
                            [sys.executable, "schwab_streamer.py"],
                            stdout=sys.stdout,
                            stderr=sys.stderr
                        )
                    processes[i] = new_proc
                    logger.info(f"   ✓ {service_name} restarted (PID: {new_proc.pid})")
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        cleanup()



