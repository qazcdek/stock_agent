from typing import Dict
from stock_agent.infra.brokers.paper_broker import PaperBroker
from stock_agent.monitoring.logger import logger

class BacktestBroker(PaperBroker):
    """Simulated broker specifically calibrated to accept historical price feeds for backtesting."""
    def __init__(self, initial_cash: float = 10000000.0):
        super().__init__(initial_cash)
        self.mock_prices: Dict[str, float] = {}

    def set_current_price(self, ticker: str, price: float) -> None:
        """Injects current historical bar price during a backtest run."""
        self.mock_prices[ticker] = price

    async def get_current_price(self, ticker: str) -> float:
        price = self.mock_prices.get(ticker)
        if price is None:
            # Fallback to standard base values
            price = 50000.0
            logger.debug("No backtest price injected. Using default.", ticker=ticker, price=price)
        return price
