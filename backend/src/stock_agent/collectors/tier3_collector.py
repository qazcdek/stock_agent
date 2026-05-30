import asyncio
from typing import List, Dict
from stock_agent.common.dto import ActiveListUpdatedEvent, Orderbook, Tick
from stock_agent.common.event_bus import event_bus
from stock_agent.common.calendar import trading_calendar
from stock_agent.collectors.scheduler import get_market_for_ticker
from stock_agent.monitoring.logger import logger

class Tier3ActiveCollector:
    def __init__(self):
        self.active_tickers: List[str] = []
        self._connections: Dict[str, asyncio.Task] = {}
        self.is_running = False

    def start(self):
        """Starts the Tier 3 listener for active trading symbols."""
        logger.info("Starting Tier 3 Active Collector...")
        event_bus.subscribe("ActiveListUpdated", self._on_active_list_updated)
        self.is_running = True

    async def stop(self):
        self.is_running = False
        for ticker, task in self._connections.items():
            task.cancel()
        self._connections.clear()
        logger.info("Tier 3 Active Collector stopped.")

    async def _on_active_list_updated(self, event: ActiveListUpdatedEvent):
        new_active = event.tickers[:10]  # Max 10 limit for Tier 3
        logger.info(f"Tier 3 Active List updated: {new_active}")
        
        # Disconnect removed tickers
        removed = set(self.active_tickers) - set(new_active)
        for ticker in removed:
            if ticker in self._connections:
                logger.info(f"Disconnecting WebSocket for {ticker}")
                self._connections[ticker].cancel()
                del self._connections[ticker]

        # Connect new tickers
        added = set(new_active) - set(self.active_tickers)
        for ticker in added:
            market = get_market_for_ticker(ticker)
            if not trading_calendar.is_market_open(market):
                logger.warning(f"Market {market.value} is closed for {ticker}, won't connect WS now.")
                continue
                
            logger.info(f"Connecting WebSocket for {ticker}")
            self._connections[ticker] = asyncio.create_task(self._websocket_loop(ticker))
            
        self.active_tickers = new_active

    async def _websocket_loop(self, ticker: str):
        """Simulate a WebSocket streaming connection for a ticker."""
        try:
            while self.is_running:
                # In real implementation, this would be `async for msg in ws:`
                await asyncio.sleep(1)
                
                # Check if market closed while running
                market = get_market_for_ticker(ticker)
                if not trading_calendar.is_market_open(market):
                    logger.info(f"Market {market.value} closed. Disconnecting WS for {ticker}")
                    break

                # Mock event publishing
                # await event_bus.publish(OrderbookUpdatedEvent(...))
                # await event_bus.publish(TickEvent(...))
                
        except asyncio.CancelledError:
            logger.debug(f"WebSocket task for {ticker} cancelled.")
        except Exception as e:
            logger.error(f"WebSocket error for {ticker}: {e}")
        finally:
            if ticker in self._connections:
                del self._connections[ticker]

tier3_collector = Tier3ActiveCollector()
