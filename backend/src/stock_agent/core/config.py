import os
import json
from typing import List, Optional, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # System settings
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    
    # DB settings
    SQLITE_URL: str = Field(default="sqlite:///./stock_agent.db")
    BACKTEST_SQLITE_URL: str = Field(default="sqlite:///./stock_agent_backtest.db")
    POSTGRES_URL: Optional[str] = Field(default="postgresql+psycopg2://postgres:postgres@localhost:5432/stock_agent")
    MONGODB_URL: Optional[str] = Field(default="mongodb://localhost:27017/stock_agent")
    CLICKHOUSE_URL: Optional[str] = Field(default="clickhouse://localhost:9000/default")
    DUCKDB_PATH: str = Field(default="stock_agent_analytics.db")

    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4-turbo")
    
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022")

    # Advanced LLM Configuration (Lifespan and Multi-Agent Setup)
    # Format: provider:model_name[:api_base_url]
    LLM_FAST: Optional[str] = Field(default="chatgpt:gpt-4-turbo")
    LLM_DEEP: Optional[str] = Field(default="claude:claude-3-5-sonnet-20241022")
    
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    
    VLLM_API_BASE: Optional[str] = Field(default="http://localhost:8000/v1")
    VLLM_API_KEY: Optional[str] = Field(default=None)

    FMP_API_KEY: Optional[str] = Field(default=None)
    DART_API_KEY: Optional[str] = Field(default=None)
    NAVER_CLIENT_ID: Optional[str] = Field(default=None)
    NAVER_CLIENT_SECRET: Optional[str] = Field(default=None)

    # KIS API Credentials
    KIS_APP_KEY: Optional[str] = Field(default=None)
    KIS_APP_SECRET: Optional[str] = Field(default=None)
    KIS_ACCOUNT_NO: Optional[str] = Field(default=None)
    KIS_CANO: Optional[str] = Field(default=None)
    KIS_ACNT_PRDT_CD: Optional[str] = Field(default="01")
    KIS_URL: str = Field(default="https://openapimts.koreainvestment.com:29443")

    # Notifiers
    SLACK_WEBHOOK_URL: Optional[str] = Field(default=None)
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None)
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None)

    # Strategy Parameters
    TRADING_UNIVERSE: Any = Field(default_factory=lambda: ["005930", "000660", "035420"])
    MAX_DAILY_ORDER_AMOUNT: float = Field(default=5000000.0)
    MAX_POSITION_RATIO: float = Field(default=0.3)
    RISK_STOP_LOSS_PCT: float = Field(default=0.05)
    RISK_TAKE_PROFIT_PCT: float = Field(default=0.15)

    @field_validator("TRADING_UNIVERSE", mode="before")
    @classmethod
    def parse_trading_universe(cls, v):
        if isinstance(v, str):
            # Clean inline comments
            v = v.split("#")[0].strip()
            # If it's a JSON array format
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            # Comma-separated string format
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # Load environment settings from .env file if available
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton Settings Instance
settings = Settings()
