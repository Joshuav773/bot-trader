"""
Polling-based order flow streamer for Polygon.io REST API.
Captures large trades (>= $500k) and records price impact snapshots.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import requests
from sqlmodel import Session

from api.db import engine
from order_flow.aggregator import process_trade, get_sp500_tickers
from order_flow.price_tracker import process_snapshots_for_order
from data_ingestion.polygon_client import PolygonDataClient
from config.settings import POLYGON_API_KEY


logger = logging.getLogger(__name__)


class OrderFlowStreamer:
    """
    Streams trades from Polygon via REST polling and filters for large orders.
    """

    def __init__(self, api_key: Optional[str] = POLYGON_API_KEY):
        self.api_key = api_key
        self.polygon_client = PolygonDataClient(api_key) if api_key else None
        self.running = False
        self.poll_interval = int(os.getenv("ORDER_FLOW_POLL_INTERVAL", "120"))  # seconds
        self.lookback_minutes = int(os.getenv("ORDER_FLOW_LOOKBACK_MINUTES", "5"))
        self.max_tickers = int(os.getenv("ORDER_FLOW_MAX_TICKERS", "10"))
        tickers_env = os.getenv("ORDER_FLOW_TICKERS")
        if tickers_env:
            self.tickers = [t.strip().upper() for t in tickers_env.split(",") if t.strip()]
        else:
            self.tickers = get_sp500_tickers()[: self.max_tickers]
        self.last_timestamp_ns: Dict[str, Optional[int]] = {ticker: None for ticker in self.tickers}
        self.session = requests.Session()

    async def start(self):
        """Start polling loop."""
        if not self.api_key:
            logger.warning("Polygon API key not set. Order flow streaming disabled.")
            return

        self.running = True
        logger.info(
            "Order flow streamer started for %s tickers (poll interval %ss, lookback %sm)",
            len(self.tickers),
            self.poll_interval,
            self.lookback_minutes,
        )

        try:
            while self.running:
                start_time = datetime.now(timezone.utc)
                try:
                    await self._poll_recent_trades()
                except Exception as exc:
                    logger.exception("Error while polling order flow trades: %s", exc)
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                sleep_for = max(self.poll_interval - elapsed, 5)
                await asyncio.sleep(sleep_for)
        finally:
            self.session.close()

    async def _poll_recent_trades(self):
        """Poll Polygon REST API for recent trades and persist large orders."""
        loop = asyncio.get_running_loop()
        tasks = []
        now_ns = int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        since_ns_default = now_ns - int(self.lookback_minutes * 60 * 1_000_000_000)

        for ticker in self.tickers:
            since_ns = self.last_timestamp_ns.get(ticker) or since_ns_default
            task = loop.run_in_executor(
                None,
                self._fetch_and_process_trades,
                ticker,
                since_ns,
                now_ns,
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

    def _fetch_and_process_trades(self, ticker: str, since_ns: int, until_ns: int) -> None:
        """Fetch trades for a single ticker and process them."""
        url = f"https://api.polygon.io/v3/trades/{ticker}"
        params = {
            "timestamp.gte": since_ns,
            "timestamp.lte": until_ns,
            "order": "asc",
            "limit": 500,
            "apiKey": self.api_key,
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch trades for %s: %s", ticker, exc)
            return

        results = payload.get("results", []) or []
        if not results:
            return

        latest_ts = since_ns
        with Session(engine) as session:
            for trade in results:
                price = trade.get("price") or trade.get("p")
                size = trade.get("size") or trade.get("s") or trade.get("volume")
                if not price or not size:
                    continue

                timestamp_ns = (
                    trade.get("sip_timestamp")
                    or trade.get("participant_timestamp")
                    or trade.get("trf_timestamp")
                    or trade.get("timestamp")
                )
                if timestamp_ns:
                    latest_ts = max(latest_ts, int(timestamp_ns))

                trade_payload = {
                    "ticker": ticker,
                    "price": price,
                    "size": size,
                    "side": trade.get("conditions", ["buy"])[0] if trade.get("conditions") else "buy",
                    "timestamp": timestamp_ns,
                }

                order = process_trade(trade_payload, session)
                if order:
                    try:
                        process_snapshots_for_order(order, session, self.polygon_client or PolygonDataClient(self.api_key))
                    except Exception as exc:
                        logger.debug("Snapshot collection failed for order %s: %s", order.id, exc)

        self.last_timestamp_ns[ticker] = latest_ts

    def stop(self):
        """Stop streaming."""
        self.running = False
        logger.info("Order flow streamer stopping…")


async def _main():
    logging.basicConfig(level=logging.INFO)
    streamer = OrderFlowStreamer()
    try:
        await streamer.start()
    except KeyboardInterrupt:
        streamer.stop()


if __name__ == "__main__":
    asyncio.run(_main())