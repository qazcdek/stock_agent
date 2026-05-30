import uuid
from typing import Dict, List, Optional, Any
from stock_agent.common.dto import (
    OrderApprovedEvent,
    OrderIntent,
    OrderRejectedEvent,
    Order,
    OrderStatus
)
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer


class ApprovalQueue:
    def __init__(self, automated: bool = False):
        self.automated = automated
        # Store pending intents: queue_id -> OrderIntent
        self._queue: Dict[str, OrderIntent] = {}
        
        event_bus.subscribe("OrderApproved", self.on_order_approved)
        logger.info("ApprovalQueue initialized and subscribed to OrderApprovedEvent", automated=self.automated)

    def set_mode(self, automated: bool):
        self.automated = automated
        logger.info("ApprovalQueue mode updated", automated=self.automated)

    def get_pending(self) -> List[Dict]:
        """Return list of pending intents in queue format."""
        return [
            {
                "queue_id": q_id,
                "ticker": intent.ticker,
                "action": intent.action.value,
                "quantity": intent.quantity,
                "price": intent.price,
                "timestamp": intent.timestamp.isoformat(),
                "source": intent.source_strategy
            }
            for q_id, intent in self._queue.items()
        ]

    async def on_order_approved(self, event: OrderApprovedEvent):
        intent = event.intent
        
        if self.automated:
            # Skip queue, immediately forward to OMS by converting into an Order
            logger.info("ApprovalQueue [Automated Mode]: forwarding intent straight to OMS", ticker=intent.ticker)
            await self._forward_to_oms(intent)
        else:
            # Place in pending user queue
            queue_id = str(uuid.uuid4())
            self._queue[queue_id] = intent
            logger.info("ApprovalQueue [Manual Mode]: order placed in manual queue", queue_id=queue_id, ticker=intent.ticker)
            
            # Publish notification event for the WebSocket
            await event_bus.publish(QueueUpdatedEvent(queue_id=queue_id, intent=intent, action="PENDING"))

    async def approve_intent(self, queue_id: str) -> bool:
        """User clicked 'APPROVE' on Web UI."""
        intent = self._queue.pop(queue_id, None)
        if not intent:
            logger.warn("ApprovalQueue: Attempted to approve non-existent queue_id", queue_id=queue_id)
            return False
            
        logger.info("ApprovalQueue: User APPROVED intent", queue_id=queue_id, ticker=intent.ticker)
        await self._forward_to_oms(intent)
        await event_bus.publish(QueueUpdatedEvent(queue_id=queue_id, intent=intent, action="APPROVED"))
        return True

    async def reject_intent(self, queue_id: str, reason: str = "User manual rejection") -> bool:
        """User clicked 'REJECT' on Web UI."""
        intent = self._queue.pop(queue_id, None)
        if not intent:
            logger.warn("ApprovalQueue: Attempted to reject non-existent queue_id", queue_id=queue_id)
            return False
            
        logger.info("ApprovalQueue: User REJECTED intent", queue_id=queue_id, ticker=intent.ticker)
        await event_bus.publish(OrderRejectedEvent(intent=intent, reason=reason))
        await event_bus.publish(QueueUpdatedEvent(queue_id=queue_id, intent=intent, action="REJECTED"))
        return True

    async def _forward_to_oms(self, intent: OrderIntent):
        """Build a concrete Order object and send it to OMS by publishing an event."""
        order = Order(
            order_id=f"ord_{uuid.uuid4().hex[:8]}",
            ticker=intent.ticker,
            action=intent.action,
            quantity=intent.quantity,
            price=intent.price,
            status=OrderStatus.PENDING,
            timestamp=intent.timestamp
        )
        
        # Save initially to RDB
        storage_layer.save_order(order)
        
        # Dispatch OrderConfirmedEvent which the OMS listens to
        from stock_agent.common.dto import Event
        await event_bus.publish(OrderConfirmedEvent(order=order))


# Dynamic events to communicate with Web Dashboard
class QueueUpdatedEvent(OrderApprovedEvent):
    event_type: str = "QueueUpdated"
    queue_id: str
    action: str  # PENDING, APPROVED, REJECTED


class OrderConfirmedEvent(OrderApprovedEvent):
    event_type: str = "OrderConfirmed"
    order: Order
    # Inherit or build cleanly
    intent: Any = None


# Global Approval Queue Instance (default to Manual for interactive demo, can toggle)
approval_queue = ApprovalQueue(automated=False)
