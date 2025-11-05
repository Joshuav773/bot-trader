"""
Real-time trade streamer for Polygon.io WebSocket API.
Captures trades and filters for large orders >= $500k.
"""
import asyncio
import json
import logging
from typing import Set, Optional
from datetime import datetime

from polygon import RESTClient
from sqlmodel import Session

from api.db import engine
from order_flow.aggregator import process_trade, get_sp500_tickers
from order_flow.price_tracker import process_snapshots_for_order
from data_ingestion.polygon_client import PolygonDataClient
from config.settings import POLYGON_API_KEY


logger = logging.getLogger(__name__)


class OrderFlowStreamer:
    """
    Streams real-time trades from Polygon and filters for large orders.
    Note: Polygon WebSocket requires a paid plan. For now, this is a polling-based fallback.
    """
    
    def __init__(self, api_key: Optional[str] = POLYGON_API_KEY):
        self.api_key = api_key
        self.client = RESTClient(api_key) if api_key else None
        self.polygon_client = PolygonDataClient(api_key) if api_key else None
        self.tickers = get_sp500_tickers()
        self.running = False
    
    async def start(self):
        """Start streaming (polling mode for now until WebSocket is configured)."""
        if not self.api_key:
            logger.warning("Polygon API key not set. Order flow streaming disabled.")
            return
        
        self.running = True
        logger.info(f"Starting order flow streamer for {len(self.tickers)} S&P 500 tickers")
        
        # For now, use polling every 60s to check for recent large trades
        # TODO: Replace with WebSocket when Polygon WebSocket is configured
        while self.running:
            try:
                await self._poll_recent_trades()
                await asyncio.sleep(60)  # Poll every 60 seconds
            except Exception as e:
                logger.error(f"Error in order flow streamer: {e}")
                await asyncio.sleep(60)
    
    async def _poll_recent_trades(self):
        """Poll recent trades and process large orders."""
        # TODO: Implement WebSocket or polling-based trade capture
        # For now, this is a placeholder that logs the intent
        logger.debug("Polling for recent large trades...")
        # Actual implementation would:
        # 1. Connect to Polygon WebSocket or use REST trades endpoint
        # 2. Process each trade through process_trade()
        # 3. Capture price snapshots for new orders
    
    def stop(self):
        """Stop streaming."""
        self.running = False
        logger.info("Order flow streamer stopped")

