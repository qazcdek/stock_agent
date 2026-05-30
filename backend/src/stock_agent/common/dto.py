from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Bar(BaseModel):
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SignalCandidate(BaseModel):
    ticker: str
    timestamp: datetime
    action: ActionType
    source_agent: str  # e.g., "TechnicalAnalyst", "MLAnalyst"
    weight: float      # e.g., 0.0 to 1.0 confidence
    reason: str


class OrderIntent(BaseModel):
    ticker: str
    action: ActionType
    quantity: int
    price: float
    timestamp: datetime
    source_strategy: str = "DefaultStrategy"


class Order(BaseModel):
    order_id: str
    ticker: str
    action: ActionType
    quantity: int
    price: float
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    retries: int = 0
    reason: Optional[str] = None


class Position(BaseModel):
    ticker: str
    quantity: int
    avg_price: float
    current_price: float
    floating_pnl: float = 0.0

    def update_price(self, price: float):
        self.current_price = price
        self.floating_pnl = (self.current_price - self.avg_price) * self.quantity


# ----------------- Events -----------------

class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str


class RawDataCollectedEvent(Event):
    event_type: str = "RawDataCollected"
    ticker: str
    bar: Bar


class FeaturesComputedEvent(Event):
    event_type: str = "FeaturesComputed"
    ticker: str
    bar: Bar
    features: Dict[str, Any]


class OrderIntentGeneratedEvent(Event):
    event_type: str = "OrderIntentGenerated"
    intent: OrderIntent


class OrderApprovedEvent(Event):
    event_type: str = "OrderApproved"
    intent: OrderIntent


class OrderRejectedEvent(Event):
    event_type: str = "OrderRejected"
    intent: OrderIntent
    reason: str


class OrderSubmittedEvent(Event):
    event_type: str = "OrderSubmitted"
    order: Order


class OrderFilledEvent(Event):
    event_type: str = "OrderFilled"
    order: Order


class OrderCancelledEvent(Event):
    event_type: str = "OrderCancelled"
    order: Order


class PortfolioUpdatedEvent(Event):
    event_type: str = "PortfolioUpdated"
    positions: Dict[str, Position]
    total_value: float
    cash: float
    floating_pnl: float


class NotificationEvent(Event):
    event_type: str = "Notification"
    level: str  # INFO, WARNING, ERROR, SUCCESS
    message: str


class NewsArticle(BaseModel):
    url: str
    title: str
    summary: str
    source: str
    published_at: datetime
    category: str = "finance_economics"
    ticker: Optional[str] = None


class RawNewsCollectedEvent(Event):
    event_type: str = "RawNewsCollected"
    article: NewsArticle


# ----------------- Tier 2/3 Data DTOs -----------------

class Orderbook(BaseModel):
    ticker: str
    timestamp: datetime
    bids: list[tuple[float, float]]  # [(price, size), ...]
    asks: list[tuple[float, float]]  # [(price, size), ...]


class Tick(BaseModel):
    ticker: str
    timestamp: datetime
    price: float
    size: float
    is_buy: bool


class WatchlistUpdatedEvent(Event):
    event_type: str = "WatchlistUpdated"
    tickers: list[str]


class ActiveListUpdatedEvent(Event):
    event_type: str = "ActiveListUpdated"
    tickers: list[str]
