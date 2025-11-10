"""
Polling-based order flow streamer for Polygon.io or Finnhub REST APIs.
Captures large trades (>= $500k) and records price impact snapshots.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone, time as time_cls
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import requests
from sqlmodel import Session

from api.db import engine
from config.settings import (
    FINNHUB_API_KEY,
    ORDER_FLOW_EQUITY_BATCH_SIZE,
    ORDER_FLOW_EQUITY_SESSION,
    ORDER_FLOW_FOREX_BATCH_SIZE,
    ORDER_FLOW_FOREX_SHUTDOWN_WEEKENDS,
    ORDER_FLOW_LOOKBACK_MINUTES,
    ORDER_FLOW_MAX_EQUITY_TICKERS,
    ORDER_FLOW_MAX_FOREX_TICKERS,
    ORDER_FLOW_POLL_INTERVAL,
    ORDER_FLOW_PROVIDER,
    ORDER_FLOW_TIMEZONE,
    ORDER_FLOW_HEARTBEAT_MINUTES,
    POLYGON_API_KEY,
)
from data_ingestion.finnhub_client import FinnhubClient
from data_ingestion.polygon_client import PolygonDataClient
from order_flow.aggregator import (
    get_major_forex_pairs,
    get_sp500_tickers,
    process_trade,
)
from order_flow.price_tracker import process_snapshots_for_order

logger = logging.getLogger(__name__)


def _chunk(items: Sequence[str], size: int) -> List[List[str]]:
    size = max(size, 1)
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


class OrderFlowStreamer:
    """
    Streams trades from Polygon or Finnhub via REST polling and filters for large orders.
    """

    def __init__(
        self,
        provider: str = ORDER_FLOW_PROVIDER,
        polygon_key: Optional[str] = POLYGON_API_KEY,
        finnhub_key: Optional[str] = FINNHUB_API_KEY,
    ):
        self.provider = provider
        self.poll_interval = ORDER_FLOW_POLL_INTERVAL
        self.lookback_minutes = ORDER_FLOW_LOOKBACK_MINUTES
        self.running = False
        self.heartbeat_every = timedelta(minutes=max(ORDER_FLOW_HEARTBEAT_MINUTES, 1))
        self._last_heartbeat: Optional[datetime] = None

        # Market hours handling
        self.market_tz = ZoneInfo(ORDER_FLOW_TIMEZONE)
        self.equity_start, self.equity_end = (
            datetime.strptime(ORDER_FLOW_EQUITY_SESSION[0], "%H:%M").time(),
            datetime.strptime(ORDER_FLOW_EQUITY_SESSION[1], "%H:%M").time(),
        )

        # Prepare universes
        env_tickers = os.getenv("ORDER_FLOW_TICKERS")
        if env_tickers:
            universe = [t.strip().upper() for t in env_tickers.split(",") if t.strip()]
            equities = [t for t in universe if not t.startswith("C:")]
            forex = [t for t in universe if t.startswith("C:") or len(t) == 6]
        else:
            equities = get_sp500_tickers()[:ORDER_FLOW_MAX_EQUITY_TICKERS]
            forex = get_major_forex_pairs()[:ORDER_FLOW_MAX_FOREX_TICKERS]

        self.equity_batches = _chunk(equities, ORDER_FLOW_EQUITY_BATCH_SIZE)
        self.forex_batches = _chunk(forex, ORDER_FLOW_FOREX_BATCH_SIZE)
        self._equity_batch_idx = 0
        self._forex_batch_idx = 0

        all_tickers = equities + forex
        self.last_timestamp_ns: Dict[str, Optional[int]] = {ticker: None for ticker in all_tickers}

        # Data providers
        self.polygon_client = PolygonDataClient(polygon_key) if polygon_key else None
        self.finnhub_client = FinnhubClient(finnhub_key) if finnhub_key and provider == "finnhub" else None

        if provider == "polygon" and not polygon_key:
            logger.warning("ORDER_FLOW_PROVIDER=polygon but POLYGON_API_KEY not set. Switching to Finnhub if available.")
            if finnhub_key:
                self.provider = "finnhub"
                self.finnhub_client = FinnhubClient(finnhub_key)
            else:
                raise RuntimeError("No market data provider configured for order flow streamer.")

        if provider == "finnhub" and not self.finnhub_client:
            raise RuntimeError("ORDER_FLOW_PROVIDER=finnhub but FINNHUB_API_KEY is missing.")

        if not self.equity_batches and not self.forex_batches:
            raise RuntimeError("No tickers configured for order flow streaming.")

    async def start(self):
        """Start polling loop."""
        self.running = True
        logger.info(
            "Order flow streamer starting with provider=%s | equities=%d (batch=%d) | forex=%d (batch=%d)",
            self.provider,
            sum(len(b) for b in self.equity_batches),
            ORDER_FLOW_EQUITY_BATCH_SIZE,
            sum(len(b) for b in self.forex_batches),
            ORDER_FLOW_FOREX_BATCH_SIZE,
        )

        while self.running:
            start_time = datetime.now(timezone.utc)
            try:
                await self._poll_recent_trades()
            except Exception as exc:
                logger.exception("Error while polling order flow trades: %s", exc)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            sleep_for = max(self.poll_interval - elapsed, 5)
            await asyncio.sleep(sleep_for)

    async def _poll_recent_trades(self):
        now = datetime.now(timezone.utc)
        now_ns = int(now.timestamp() * 1_000_000_000)
        since_ns_default = now_ns - int(self.lookback_minutes * 60 * 1_000_000_000)

        # Equities during market hours
        if self._market_open_equities(now) and self.equity_batches:
            batch = self.equity_batches[self._equity_batch_idx]
            self._equity_batch_idx = (self._equity_batch_idx + 1) % len(self.equity_batches)
            self._process_batch(batch, "equity", since_ns_default, now_ns)
        else:
            logger.debug("Equity market closed; skipping equity batch.")

        # Forex (skip weekends if requested)
        if self._market_open_forex(now) and self.forex_batches:
            batch = self.forex_batches[self._forex_batch_idx]
            self._forex_batch_idx = (self._forex_batch_idx + 1) % len(self.forex_batches)
            self._process_batch(batch, "forex", since_ns_default, now_ns)

        self._emit_heartbeat(now)

    def _process_batch(self, tickers: Iterable[str], asset_class: str, default_since_ns: int, now_ns: int) -> None:
        for ticker in tickers:
            since_ns = self.last_timestamp_ns.get(ticker) or default_since_ns
            try:
                trades, latest_ts = self._fetch_trades(ticker, since_ns, now_ns, asset_class)
            except Exception as exc:
                logger.debug("Failed to fetch trades for %s via %s: %s", ticker, self.provider, exc)
                continue

            if latest_ts:
                self.last_timestamp_ns[ticker] = latest_ts

            if not trades:
                continue

            with Session(engine) as session:
                for trade in trades:
                    order = process_trade(trade, session)
                    if order:
                        try:
                            market_client = self.polygon_client if self.polygon_client else self.finnhub_client
                            process_snapshots_for_order(order, session, market_client)
                        except Exception as exc:
                            logger.debug("Snapshot collection failed for order %s: %s", order.id, exc)

    def _fetch_trades(
        self,
        ticker: str,
        since_ns: int,
        until_ns: int,
        asset_class: str,
    ) -> Tuple[List[Dict], Optional[int]]:
        if self.provider == "finnhub":
            return self._fetch_trades_finnhub(ticker, since_ns, until_ns, asset_class)
        return self._fetch_trades_polygon(ticker, since_ns, until_ns)

    def _fetch_trades_polygon(self, ticker: str, since_ns: int, until_ns: int) -> Tuple[List[Dict], Optional[int]]:
        if not self.polygon_client:
            raise RuntimeError("Polygon client not configured")
        url = f"https://api.polygon.io/v3/trades/{ticker}"
        params = {
            "timestamp.gte": since_ns,
            "timestamp.lte": until_ns,
            "order": "asc",
            "limit": 500,
            "apiKey": self.polygon_client.client.api_key if hasattr(self.polygon_client, "client") else POLYGON_API_KEY,
        }
        session = self.polygon_client.client._session if hasattr(self.polygon_client, "client") else None
        session = session or getattr(self.polygon_client, "session", None)
        session = session or requests.Session()
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("results", []) or []
        trades: List[Dict] = []
        latest_ts = since_ns
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
            trades.append(
                {
                    "ticker": ticker,
                    "price": price,
                    "size": size,
                    "side": trade.get("conditions", ["buy"])[0] if trade.get("conditions") else "buy",
                    "timestamp": timestamp_ns,
                }
            )
        return trades, latest_ts if trades else None

    def _fetch_trades_finnhub(
        self,
        ticker: str,
        since_ns: int,
        until_ns: int,
        asset_class: str,
    ) -> Tuple[List[Dict], Optional[int]]:
        if not self.finnhub_client:
            raise RuntimeError("Finnhub client not configured")

        since_dt = datetime.fromtimestamp(since_ns / 1_000_000_000, tz=timezone.utc)
        until_dt = datetime.fromtimestamp(until_ns / 1_000_000_000, tz=timezone.utc)

        if asset_class == "equity":
            raw_trades = self.finnhub_client.get_stock_trades(ticker, since_dt, until_dt)
            trades: List[Dict] = []
            latest_ts = since_ns
            for trade in raw_trades:
                price = trade.get("p")
                size = trade.get("s")
                ts = trade.get("t")
                if price is None or size is None or ts is None:
                    continue
                # Finnhub returns timestamps in ns
                timestamp_ns = int(ts)
                latest_ts = max(latest_ts, timestamp_ns)
                trades.append(
                    {
                        "ticker": ticker,
                        "price": price,
                        "size": size,
                        "side": "buy",
                        "timestamp": timestamp_ns,
                    }
                )
            return trades, latest_ts if trades else None

        # Forex fallback to candle synthesis
        raw_trades = self.finnhub_client.get_forex_trades(ticker, since_dt, until_dt)
        trades = []
        latest_ts = since_ns
        for trade in raw_trades:
            price = trade.get("price")
            volume = trade.get("volume")
            timestamp_ns = int(trade.get("timestamp", 0))
            if price is None or volume is None or timestamp_ns == 0:
                continue
            latest_ts = max(latest_ts, timestamp_ns)
            trades.append(
                {
                    "ticker": ticker,
                    "price": price,
                    "size": volume,
                    "side": trade.get("side", "buy"),
                    "timestamp": timestamp_ns,
                }
            )
        return trades, latest_ts if trades else None

    def _market_open_equities(self, now: datetime) -> bool:
        local = now.astimezone(self.market_tz)
        if local.weekday() >= 5:  # Saturday/Sunday
            return False
        start = time_cls.fromisoformat(ORDER_FLOW_EQUITY_SESSION[0])
        end = time_cls.fromisoformat(ORDER_FLOW_EQUITY_SESSION[1])
        return start <= local.time() <= end

    def _market_open_forex(self, now: datetime) -> bool:
        if not ORDER_FLOW_FOREX_SHUTDOWN_WEEKENDS:
            return True
        local = now.astimezone(self.market_tz)
        return local.weekday() < 5 or (local.weekday() == 6 and local.time() >= time_cls(hour=17))

    def _emit_heartbeat(self, now: datetime) -> None:
        if not self._last_heartbeat or now - self._last_heartbeat >= self.heartbeat_every:
            equity_symbols = sum(len(batch) for batch in self.equity_batches)
            fx_symbols = sum(len(batch) for batch in self.forex_batches)
            logger.info(
                "Heartbeat | provider=%s | equities=%d | forex=%d | poll_interval=%ss",
                self.provider,
                equity_symbols,
                fx_symbols,
                self.poll_interval,
            )
            self._last_heartbeat = now

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