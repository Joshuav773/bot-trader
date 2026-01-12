"""
FastAPI Backend - Bot Trader
Simple API for Schwab streaming service.
"""
from fastapi import FastAPI

app = FastAPI(title="Bot Trader API", version="1.0.0")


@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Bot Trader API", "status": "running"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/status")
def get_status():
    """Get service status"""
    return {
        "service": "bot-trader",
        "status": "running",
        "version": "1.0.0"
    }


