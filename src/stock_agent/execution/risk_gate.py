from typing import Tuple
from stock_agent.core.config import settings
from stock_agent.core.schemas import Order, PortfolioState
from stock_agent.monitoring.logger import logger

class RiskGate:
    def __init__(self):
        pass

    def validate_order(self, order: Order, portfolio: PortfolioState, daily_traded_amount: float) -> Tuple[bool, str]:
        """Audits candidate orders against risk profiles before allowing broker dispatch."""
        order_value = order.quantity * order.price
        
        # 1. Ensure order does not exceed cash liquidity
        if order.action == "BUY" and order_value > portfolio.cash:
            reason = f"Cash restriction: Order value ({order_value:,.0f} KRW) exceeds current cash balance ({portfolio.cash:,.0f} KRW)."
            logger.warning("Risk gate rejected order", reason=reason)
            return False, reason

        # 2. Check single order ceiling constraint
        # Let's say max single order is capped at 50% of the total daily limit for safety
        max_single_order = settings.MAX_DAILY_ORDER_AMOUNT * 0.5
        if order_value > max_single_order:
            reason = f"Single order limit breach: Order value ({order_value:,.0f} KRW) exceeds max single limit ({max_single_order:,.0f} KRW)."
            logger.warning("Risk gate rejected order", reason=reason)
            return False, reason

        # 3. Check cumulative daily trading amount limit
        if daily_traded_amount + order_value > settings.MAX_DAILY_ORDER_AMOUNT:
            reason = (
                f"Daily aggregate limit breach: Cumulative traded amount ({daily_traded_amount:,.0f} KRW) "
                f"+ candidate order ({order_value:,.0f} KRW) exceeds daily hard cap ({settings.MAX_DAILY_ORDER_AMOUNT:,.0f} KRW)."
            )
            logger.warning("Risk gate rejected order", reason=reason)
            return False, reason

        logger.info("Order cleared through risk gate rules", ticker=order.ticker, order_value=order_value)
        return True, "Approved"
