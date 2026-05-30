import os
import httpx
import openai
import anthropic
from typing import Optional
from stock_agent.core.config import settings
from stock_agent.core.interfaces import LLMClient
from stock_agent.monitoring.logger import logger

class ChatGPTClient(LLMClient):
    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            logger.warning(f"OPENAI_API_KEY is not set. ChatGPT client for {model} will fail.")
            self.client = None
        else:
            self.client = openai.AsyncOpenAI(api_key=self.api_key)

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.client:
            logger.error("ChatGPT client not initialized (missing API key). Returning empty.")
            return "Error: ChatGPT client not initialized."
        try:
            logger.debug("Sending request to ChatGPT", model=self.model, temperature=temperature)
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
            logger.error(f"Failed to call ChatGPT API ({self.model})", error=str(e))
            raise e

    async def close(self):
        if self.client:
            try:
                await self.client.close()
            except AttributeError:
                pass


class ClaudeClient(LLMClient):
    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            logger.warning(f"ANTHROPIC_API_KEY is not set. Claude client for {model} will fail.")
            self.client = None
        else:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.client:
            logger.error("Claude client not initialized (missing API key). Returning empty.")
            return "Error: Claude client not initialized."
        try:
            logger.debug("Sending request to Claude", model=self.model, temperature=temperature)
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response.content[0].text
            return content if content else ""
        except Exception as e:
            logger.error(f"Failed to call Claude API ({self.model})", error=str(e))
            raise e

    async def close(self):
        if self.client:
            try:
                await self.client.close()
            except AttributeError:
                pass


class GeminiClient(LLMClient):
    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning(f"GEMINI_API_KEY is not set. Gemini client for {model} will fail.")
        self.client = httpx.AsyncClient()

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.api_key:
            logger.error("Gemini client not initialized (missing API key). Returning empty.")
            return "Error: Gemini client not initialized."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature
            }
        }
        try:
            logger.debug("Sending request to Gemini via REST API", model=self.model, temperature=temperature)
            response = await self.client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            res_data = response.json()
            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return text if text else ""
        except Exception as e:
            logger.error(f"Failed to call Gemini API ({self.model})", error=str(e))
            raise e

    async def close(self):
        if self.client:
            await self.client.aclose()


class VLLMClient(LLMClient):
    def __init__(self, model: str, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.model = model
        self.api_base = api_base or settings.VLLM_API_BASE or "http://localhost:8000/v1"
        self.api_key = api_key or settings.VLLM_API_KEY or "token-not-needed"
        self.client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)

    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        try:
            logger.debug("Sending request to vLLM", model=self.model, base_url=self.api_base, temperature=temperature)
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
            logger.error(f"Failed to call vLLM API ({self.model} at {self.api_base})", error=str(e))
            raise e

    async def close(self):
        if self.client:
            try:
                await self.client.close()
            except AttributeError:
                pass


class LLMProvider:
    def __init__(self):
        self._fast_client: Optional[LLMClient] = None
        self._deep_client: Optional[LLMClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Explicitly initialize clients using environment settings."""
        if self._initialized:
            logger.info("LLMProvider already initialized. Re-initializing...")
            await self.close()

        logger.info("Initializing LLMProvider using settings...")
        
        # Determine fast config
        fast_config = settings.LLM_FAST or f"chatgpt:{settings.OPENAI_MODEL}"
        self._fast_client = self._create_client_from_config(fast_config)

        # Determine deep config
        deep_config = settings.LLM_DEEP or f"claude:{settings.ANTHROPIC_MODEL}"
        self._deep_client = self._create_client_from_config(deep_config)

        self._initialized = True
        logger.info("LLMProvider initialization completed.", fast_config=fast_config, deep_config=deep_config)

    def _create_client_from_config(self, config_str: str) -> LLMClient:
        parts = config_str.split(":", 2)
        provider = parts[0].strip().lower()
        model = parts[1].strip() if len(parts) > 1 else ""
        api_base = parts[2].strip() if len(parts) > 2 else None

        if provider == "chatgpt":
            return ChatGPTClient(model=model or settings.OPENAI_MODEL or "gpt-4-turbo")
        elif provider == "claude":
            return ClaudeClient(model=model or settings.ANTHROPIC_MODEL or "claude-3-5-sonnet-20241022")
        elif provider == "gemini":
            return GeminiClient(model=model or "gemini-1.5-flash")
        elif provider == "vllm":
            return VLLMClient(model=model, api_base=api_base)
        else:
            logger.warning(f"Unknown LLM provider '{provider}'. Falling back to ChatGPT.")
            return ChatGPTClient(model=model or settings.OPENAI_MODEL or "gpt-4-turbo")

    async def get_fast_client(self) -> LLMClient:
        """Returns the fast LLM client, automatically initializing if not done."""
        if not self._initialized:
            await self.initialize()
        return self._fast_client

    async def get_deep_client(self) -> LLMClient:
        """Returns the deep LLM client, automatically initializing if not done."""
        if not self._initialized:
            await self.initialize()
        return self._deep_client

    async def close(self) -> None:
        """Closes all clients, cleaning up resources."""
        if self._fast_client and hasattr(self._fast_client, "close"):
            await self._fast_client.close()
        if self._deep_client and hasattr(self._deep_client, "close"):
            await self._deep_client.close()
        self._fast_client = None
        self._deep_client = None
        self._initialized = False
        logger.info("LLMProvider successfully closed and resources released.")

# Global Singleton Instance
llm_provider = LLMProvider()


class FastLLMProxy(LLMClient):
    """Lazy-evaluated thread-safe proxy for the fast tier LLM client."""
    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        client = await llm_provider.get_fast_client()
        return await client.generate_completion(system_prompt, user_prompt, temperature)


class DeepLLMProxy(LLMClient):
    """Lazy-evaluated thread-safe proxy for the deep tier LLM client."""
    async def generate_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        client = await llm_provider.get_deep_client()
        return await client.generate_completion(system_prompt, user_prompt, temperature)
