from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from stock_agent.core.enums import Action, OrderType, OrderStatus, AgentType

class Bar(BaseModel):
    ticker: str = Field(..., description="Stock ticker code, e.g., '005930'")
    timestamp: datetime = Field(..., description="Date and time of the candle")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(..., description="Trading volume")

    class Config:
        from_attributes = True


class AgentReport(BaseModel):
    agent_type: AgentType
    ticker: str
    score: float = Field(..., description="Analysis score. Scale differs by agent (e.g. -1 to 1 or 0 to 100)")
    rationale: str = Field(..., description="Explanation of why this score was assigned")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary numerical metrics or details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Signal(BaseModel):
    ticker: str
    action: Action
    confidence: float = Field(..., description="Signal confidence level between 0.0 and 1.0")
    rationale: str = Field(..., description="Comprehensive reasoning synthesized from child agents")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class Order(BaseModel):
    order_id: str
    ticker: str
    action: Action
    order_type: OrderType
    quantity: int = Field(..., gt=0, description="Order quantity")
    price: float = Field(..., description="Limit price or execution price limit")
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Position(BaseModel):
    ticker: str
    quantity: int = Field(..., ge=0)
    avg_price: float = Field(..., description="Average acquisition cost")
    current_price: float = Field(..., description="Latest market price")
    pnl: float = Field(default=0.0, description="Realized + unrealized profit and loss")
    pnl_pct: float = Field(default=0.0, description="Profit/loss percentage")

    @field_validator("pnl_pct")
    @classmethod
    def calculate_pnl_fields(cls, v: float, info) -> float:
        # PNL calculation can be validated or updated based on inputs
        return v


class PortfolioState(BaseModel):
    cash: float = Field(..., ge=0.0, description="Available liquidity")
    total_asset: float = Field(..., ge=0.0, description="Total net asset value (Cash + Positions)")
    positions: Dict[str, Position] = Field(default_factory=dict, description="Active holdings mapped by ticker")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NewsArticle(BaseModel):
    url: str = Field(..., description="Unique URL of the news article")
    title: str = Field(..., description="Title of the article")
    summary: str = Field(..., description="Short summary/description of the article")
    source: str = Field(..., description="Source of the article, e.g. 'Naver RSS', 'Google News'")
    published_at: datetime = Field(..., description="Publication timestamp")
    category: str = Field(default="finance_economics", description="News category")

    class Config:
        from_attributes = True
