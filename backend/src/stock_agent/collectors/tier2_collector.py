import asyncio
from datetime import datetime
from typing import List
from stock_agent.common.dto import WatchlistUpdatedEvent
from stock_agent.common.event_bus import event_bus
from stock_agent.common.calendar import trading_calendar
from stock_agent.collectors.scheduler import get_market_for_ticker
from stock_agent.monitoring.logger import logger

class Tier2WatchlistCollector:
    def __init__(self):
        self.watchlist: List[str] = []
        self._polling_task: asyncio.Task | None = None
        self.is_running = False

    def start(self):
        """Starts the Tier 2 listener and polling loop."""
        logger.info("Starting Tier 2 Watchlist Collector...")
        event_bus.subscribe("WatchlistUpdated", self._on_watchlist_updated)
        self.is_running = True
        self._polling_task = asyncio.create_task(self._polling_loop())

    async def stop(self):
        self.is_running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("Tier 2 Watchlist Collector stopped.")

    async def _on_watchlist_updated(self, event: WatchlistUpdatedEvent):
        logger.info(f"Tier 2 Watchlist updated: {event.tickers}")
        self.watchlist = event.tickers[:30] # Max 30 limit

    async def _polling_loop(self):
        while self.is_running:
            try:
                for ticker in self.watchlist:
                    market = get_market_for_ticker(ticker)
                    
                    # Only collect if market is open
                    if trading_calendar.is_market_open(market):
                        await self._collect_ticker_data(ticker)
                    else:
                        logger.debug(f"Skipping {ticker} polling, market {market.value} is closed.")
                        
                # Sleep for 1 minute before next poll cycle
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Tier 2 polling loop: {e}")
                await asyncio.sleep(60)

    async def _collect_ticker_data(self, ticker: str):
        """Poll 1m OHLCV, top 10 orderbook, buy/sell pressure."""
        # TODO: Integrate real API fetcher for 1m bars and orderbook
        logger.debug(f"Polled Tier 2 data for {ticker}")

tier2_collector = Tier2WatchlistCollector()
