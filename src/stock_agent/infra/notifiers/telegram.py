import httpx
from stock_agent.core.config import settings
from stock_agent.monitoring.logger import logger

class TelegramNotifier:
    def __init__(self, bot_token: str = settings.TELEGRAM_BOT_TOKEN, chat_id: str = settings.TELEGRAM_CHAT_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send_message(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.debug("Telegram credentials not configured. Skipping notification.")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.debug("Telegram notification sent successfully.")
                    return True
                else:
                    logger.error("Telegram returned error status", status_code=response.status_code, body=response.text)
                    return False
        except Exception as e:
            logger.error("Failed to send Telegram notification", error=str(e))
            return False
