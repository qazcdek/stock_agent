import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # System settings
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    
    # DB settings
    DATABASE_URL: str = Field(default="sqlite:///./stock_agent.db")

    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4-turbo")
    
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022")

    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(default=None)

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
    TRADING_UNIVERSE: List[str] = Field(default_factory=lambda: ["005930", "000660", "035420"])
    MAX_DAILY_ORDER_AMOUNT: float = Field(default=5000000.0)
    MAX_POSITION_RATIO: float = Field(default=0.3)
    RISK_STOP_LOSS_PCT: float = Field(default=0.05)
    RISK_TAKE_PROFIT_PCT: float = Field(default=0.15)

    # Load environment settings from .env file if available
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton Settings Instance
settings = Settings()
