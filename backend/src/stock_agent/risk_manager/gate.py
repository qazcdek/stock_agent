from stock_agent.common.dto import (
    OrderIntentGeneratedEvent,
    OrderApprovedEvent,
    OrderRejectedEvent,
    ActionType
)
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer


class RiskManager:
    def __init__(self, max_single_order_value: float = 50000000.0, max_positions_count: int = 5):
        self.max_single_order_value = max_single_order_value
        self.max_positions_count = max_positions_count
        
        event_bus.subscribe("OrderIntentGenerated", self.on_order_intent_generated)
        logger.info("RiskManager initialized and subscribed to OrderIntentGeneratedEvent")

    async def on_order_intent_generated(self, event: OrderIntentGeneratedEvent):
        intent = event.intent
        ticker = intent.ticker
        value = intent.quantity * intent.price

        logger.info("RiskManager checking order intent", ticker=ticker, action=intent.action.value, quantity=intent.quantity, value=value)

        # Rule 1: Single Order Value Limit
        if value > self.max_single_order_value:
            reason = f"Order value {value:,.0f} exceeds max single order limit {self.max_single_order_value:,.0f}."
            logger.warn("RiskManager rejected intent (Single Order Cap)", ticker=ticker, reason=reason)
            await event_bus.publish(OrderRejectedEvent(intent=intent, reason=reason))
            return

        # Rule 2: Max Portfolio Position Count Cap (for BUY actions)
        if intent.action == ActionType.BUY:
            active_positions = storage_layer.get_positions()
            # If buying a new ticker, check limits
            existing_pos = next((p for p in active_positions if p.ticker == ticker), None)
            if not existing_pos and len(active_positions) >= self.max_positions_count:
                reason = f"Max positions limit ({self.max_positions_count}) reached. Cannot open new position for {ticker}."
                logger.warn("RiskManager rejected intent (Max Positions Cap)", ticker=ticker, reason=reason)
                await event_bus.publish(OrderRejectedEvent(intent=intent, reason=reason))
                return

        # Rule 3: Extreme price threshold protection (slippage / sanity check)
        if intent.price <= 0.0:
            reason = "Price must be strictly positive."
            logger.warn("RiskManager rejected intent (Zero Price)", ticker=ticker)
            await event_bus.publish(OrderRejectedEvent(intent=intent, reason=reason))
            return

        # Passed all checks!
        logger.info("RiskManager approved order intent", ticker=ticker)
        await event_bus.publish(OrderApprovedEvent(intent=intent))


# Global Risk Manager Instance
risk_manager = RiskManager()
