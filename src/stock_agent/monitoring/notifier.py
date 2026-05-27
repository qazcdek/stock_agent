import asyncio
from stock_agent.infra.notifiers.slack import SlackNotifier
from stock_agent.infra.notifiers.telegram import TelegramNotifier
from stock_agent.monitoring.logger import logger

class NotificationDispatcher:
    def __init__(self):
        self.slack = SlackNotifier()
        self.telegram = TelegramNotifier()

    async def notify(self, text: str) -> None:
        """Dispatches notification text to all configured notification channels in parallel."""
        logger.info("Dispatching system notification", message=text)
        
        tasks = []
        if self.slack.webhook_url:
            tasks.append(self.slack.send_message(text))
        if self.telegram.bot_token and self.telegram.chat_id:
            # Simple sanitization for HTML parsed telegram messages if needed, or send as-is
            tasks.append(self.telegram.send_message(text))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error("Error occurred while sending notification", error=str(res))
        else:
            logger.debug("No active notification channels configured.")

# Singleton instance
notifier = NotificationDispatcher()
