from enum import Enum

class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class AgentType(str, Enum):
    TECHNICAL = "TECHNICAL"
    FUNDAMENTAL = "FUNDAMENTAL"
    NEWS = "NEWS"
    SYNTHESIZER = "SYNTHESIZER"
