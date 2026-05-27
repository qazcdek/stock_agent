from anthropic import AsyncAnthropic
from stock_agent.core.config import settings
from stock_agent.core.interfaces import LLMClient
from stock_agent.monitoring.logger import logger

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str = settings.ANTHROPIC_API_KEY, model: str = settings.ANTHROPIC_MODEL):
        self.model = model
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY is not set. Anthropic LLM calls will fail.")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=api_key)

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.client:
            logger.error("Anthropic client not initialized (missing API key). Returning empty response.")
            return "Error: Anthropic client not initialized."
            
        try:
            logger.debug("Sending request to Anthropic", model=self.model, temperature=temperature)
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            # Extracted text from message content block
            content = response.content[0].text
            return content if content else ""
        except Exception as e:
            logger.error("Failed to call Anthropic API", error=str(e))
            raise e
