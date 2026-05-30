from datetime import datetime
from typing import List, Optional, Protocol, Dict, Any
from stock_agent.core.schemas import Bar, Signal, Order, Position, PortfolioState, NewsArticle
from stock_agent.core.enums import OrderStatus

class DataRepository(Protocol):
    """Abstract interface for persisting and reading system and market data."""
    
    async def save_bars(self, bars: List[Bar]) -> None:
        """Persist a list of market OHLCV bars."""
        ...

    async def get_bars(self, ticker: str, start_dt: datetime, end_dt: datetime) -> List[Bar]:
        """Retrieve historical bars for a ticker in a date range."""
        ...

    async def save_signal(self, signal: Signal) -> None:
        """Persist generated trading signals."""
        ...

    async def get_signals(self, ticker: Optional[str] = None, limit: int = 100) -> List[Signal]:
        """Retrieve recent trading signals."""
        ...

    async def save_order(self, order: Order) -> None:
        """Save a new order entity."""
        ...

    async def get_orders(self, ticker: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Order]:
        """Fetch orders filtered by ticker and status."""
        ...

    async def update_order(self, order_id: str, status: OrderStatus, filled_at: Optional[datetime] = None) -> Optional[Order]:
        """Update the status and fill details of an order."""
        ...

    async def save_portfolio_state(self, state: PortfolioState) -> None:
        """Snapshot current portfolio state."""
        ...

    async def get_latest_portfolio_state(self) -> Optional[PortfolioState]:
        """Get the most recent portfolio snapshot."""
        ...

    async def get_watchlist(self) -> List[str]:
        """Retrieve active tickers in the watchlist."""
        ...

    async def add_watchlist_ticker(self, ticker: str) -> None:
        """Add a ticker to the database watchlist."""
        ...

    async def remove_watchlist_ticker(self, ticker: str) -> None:
        """Remove a ticker from the database watchlist."""
        ...

    async def save_news_article(self, article: NewsArticle) -> None:
        """Persist a collected news article."""
        ...

    async def get_latest_news(self, limit: int = 50) -> List[NewsArticle]:
        """Retrieve recent news articles."""
        ...


class Broker(Protocol):
    """Abstract interface for interacting with virtual or real brokers."""

    async def place_order(self, order: Order) -> Order:
        """Submit an order to the exchange/broker. Returns the registered order."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        ...

    async def get_positions(self) -> Dict[str, Position]:
        """Retrieve current active positions from the broker."""
        ...

    async def get_balance(self) -> Dict[str, float]:
        """Fetch account balance info. Key-value of cash and total asset value."""
        ...

    async def get_current_price(self, ticker: str) -> float:
        """Fetch the latest real-time market price for a ticker."""
        ...


class LLMClient(Protocol):
    """Abstract interface for invoking Language Models (GPT, Claude, etc.)."""

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """Request text completion from the configured LLM."""
        ...
