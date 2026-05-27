import httpx
from stock_agent.core.config import settings
from stock_agent.monitoring.logger import logger

class SlackNotifier:
    def __init__(self, webhook_url: str = settings.SLACK_WEBHOOK_URL):
        self.webhook_url = webhook_url

    async def send_message(self, text: str) -> bool:
        if not self.webhook_url:
            logger.debug("Slack webhook URL not set. Skipping notification.")
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                payload = {"text": text}
                response = await client.post(self.webhook_url, json=payload)
                if response.status_code == 200:
                    logger.debug("Slack notification sent successfully.")
                    return True
                else:
                    logger.error("Slack returned error status", status_code=response.status_code, body=response.text)
                    return False
        except Exception as e:
            logger.error("Failed to send Slack notification", error=str(e))
            return False
