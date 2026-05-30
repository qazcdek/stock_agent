from stock_agent.common.dto import OrderFilledEvent, OrderRejectedEvent
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.approval_queue.queue import QueueUpdatedEvent


class NotificationSubscriber:
    def __init__(self):
        event_bus.subscribe("OrderFilled", self.on_order_filled)
        event_bus.subscribe("OrderRejected", self.on_order_rejected)
        event_bus.subscribe("QueueUpdated", self.on_queue_updated)
        logger.info("NotificationSubscriber initialized and listening on EventBus")

    async def on_order_filled(self, event: OrderFilledEvent):
        order = event.order
        message = f"🔔 [TRADE FILLED] Ticker: {order.ticker} | Action: {order.action.value} | Qty: {order.quantity} | Price: {order.avg_fill_price:,.2f}"
        self.send_telegram_notification(message)

    async def on_order_rejected(self, event: OrderRejectedEvent):
        intent = event.intent
        message = f"🚨 [RISK GATE REJECT] Rejected Intent: {intent.action.value} {intent.quantity} shares of {intent.ticker} at {intent.price:,.2f} | Reason: {event.reason}"
        self.send_telegram_notification(message)

    async def on_queue_updated(self, event: QueueUpdatedEvent):
        intent = event.intent
        if event.action == "PENDING":
            message = f"⏳ [APPROVAL REQUIRED] Awaiting manual action for {intent.action.value} {intent.quantity} shares of {intent.ticker} at {intent.price:,.2f}"
            self.send_telegram_notification(message)
        else:
            message = f"💡 [APPROVAL ACTION] Manual transaction queue action '{event.action}' taken on {intent.ticker} order."
            self.send_telegram_notification(message)

    def send_telegram_notification(self, message: str):
        """Simulate telegram notifier output via bold colorful structlog."""
        logger.info("📢 TELEGRAM NOTIFICATION SYSTEM", payload=message)


# Global instance to auto-subscribe
notification_subscriber = NotificationSubscriber()
