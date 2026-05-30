from stock_agent.common.dto import (
    Order,
    OrderStatus,
    OrderSubmittedEvent,
    OrderFilledEvent,
    OrderCancelledEvent
)
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.approval_queue.queue import OrderConfirmedEvent
from stock_agent.exchange_adapter.adapters import exchange_adapter
from stock_agent.storage.repository import storage_layer


class OMS:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        event_bus.subscribe("OrderConfirmed", self.on_order_confirmed)
        logger.info("OMS System initialized and subscribed to OrderConfirmedEvent")

    async def on_order_confirmed(self, event: OrderConfirmedEvent):
        order = event.order
        
        # State: PENDING -> SUBMITTED
        order.status = OrderStatus.SUBMITTED
        storage_layer.save_order(order)
        
        await event_bus.publish(OrderSubmittedEvent(order=order))
        logger.info("OMS: Order submitted to exchange routing", order_id=order.order_id, ticker=order.ticker)
        
        # Route and execute via adapter
        try:
            executed_order = await self._execute_with_retry(order)
            
            # Save final execution state
            storage_layer.save_order(executed_order)
            
            if executed_order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
                logger.info(
                    "OMS: Order execution success",
                    order_id=executed_order.order_id,
                    status=executed_order.status.value,
                    filled_qty=executed_order.filled_quantity,
                    avg_price=executed_order.avg_fill_price
                )
                await event_bus.publish(OrderFilledEvent(order=executed_order))
            else:
                logger.error("OMS: Order rejected or failed", order_id=executed_order.order_id, reason=executed_order.reason)
                await event_bus.publish(OrderCancelledEvent(order=executed_order))
                
        except Exception as e:
            logger.error("OMS: Extreme execution panic", order_id=order.order_id, error=str(e))
            order.status = OrderStatus.REJECTED
            order.reason = f"Execution system crash: {str(e)}"
            storage_layer.save_order(order)
            await event_bus.publish(OrderCancelledEvent(order=order))

    async def _execute_with_retry(self, order: Order) -> Order:
        """Handle retry loop for transient failures."""
        attempt = 0
        while attempt <= self.max_retries:
            try:
                result = await exchange_adapter.execute_order(order)
                if result.status != OrderStatus.REJECTED:
                    return result
                
                # If rejected/failed, increment retries
                attempt += 1
                order.retries = attempt
                order.reason = f"Execution retry attempt {attempt} failed."
                logger.warn("OMS: Order execution failed, retrying...", order_id=order.order_id, attempt=attempt)
            except Exception as e:
                attempt += 1
                order.retries = attempt
                order.reason = f"Transient exception: {str(e)}"
                logger.warn("OMS: Execution error encountered, retrying...", order_id=order.order_id, error=str(e))
                
        # Exceeded retries, mark as rejected
        order.status = OrderStatus.REJECTED
        order.reason = f"Exceeded maximum execution retries ({self.max_retries})."
        return order


# Global OMS Instance
oms_system = OMS()
