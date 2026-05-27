from openai import AsyncOpenAI
from stock_agent.core.config import settings
from stock_agent.core.interfaces import LLMClient
from stock_agent.monitoring.logger import logger

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str = settings.OPENAI_API_KEY, model: str = settings.OPENAI_MODEL):
        self.model = model
        # Handle fallback if no API key is configured
        if not api_key:
            logger.warning("OPENAI_API_KEY is not set. LLM calls will fail.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.client:
            logger.error("OpenAI client not initialized (missing API key). Returning empty response.")
            return "Error: OpenAI client not initialized."
            
        try:
            logger.debug("Sending request to OpenAI", model=self.model, temperature=temperature)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            content = response.choices[0].message.content
            return content if content else ""
        except Exception as e:
            logger.error("Failed to call OpenAI API", error=str(e))
            raise e
