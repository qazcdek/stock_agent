import math
from stock_agent.core.config import settings
from stock_agent.core.schemas import PortfolioState, Signal
from stock_agent.monitoring.logger import logger

class PositionSizer:
    def __init__(self):
        pass

    def calculate_quantity(self, signal: Signal, portfolio: PortfolioState, current_price: float) -> int:
        """Calculates optimal target quantity based on signal confidence and portfolio diversification boundaries."""
        if current_price <= 0.0:
            logger.error("Current price is invalid, cannot size position", ticker=signal.ticker, price=current_price)
            return 0

        total_asset = portfolio.total_asset
        cash = portfolio.cash

        # Retrieve active holding position if it exists
        existing_position = portfolio.positions.get(signal.ticker)
        current_holding_value = (existing_position.quantity * current_price) if existing_position else 0.0

        # Maximum KRW asset value allowed for this single ticker based on MAX_POSITION_RATIO (default: 30%)
        max_ticker_allocation = total_asset * settings.MAX_POSITION_RATIO
        
        # Remaining headroom we can buy without violating the max ticker allocation
        headroom = max_ticker_allocation - current_holding_value
        
        if headroom <= 0.0:
            logger.warning("Allocation cap reached. Zero additional units allowed.", ticker=signal.ticker, current_value=current_holding_value, cap=max_ticker_allocation)
            return 0

        # Target purchase amount is scaled by signal confidence (0.0 to 1.0) and limited by current available cash and remaining headroom
        target_purchase_value = headroom * signal.confidence
        
        # Absolute ceiling is the cash we actually have in the account
        final_purchase_value = min(target_purchase_value, cash)
        
        if final_purchase_value < current_price:
            logger.debug("Insufficient liquidity to buy even one single unit", ticker=signal.ticker, cash=cash, price=current_price)
            return 0

        quantity = math.floor(final_purchase_value / current_price)
        logger.info("Position sizing completed", ticker=signal.ticker, confidence=signal.confidence, quantity=quantity, cost=quantity*current_price)
        return quantity
