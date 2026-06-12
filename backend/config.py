"""
Configuration and settings for the Vocabulary Assistant.
Loads environment variables from .env file.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Absolute path to database file
DB_PATH = PROJECT_ROOT / "vocab.db"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Qwen / DashScope
    DASHSCOPE_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"

    # Tavily Search
    TAVILY_API_KEY: str = ""

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""

    # Database - use absolute path so it's always the same file
    DATABASE_URL: str = f"sqlite:///{DB_PATH}"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # OpenClaw
    OPENCLAW_GATEWAY_URL: str = "http://localhost:18789"
    OPENCLAW_GATEWAY_TOKEN: str = ""

    # Application
    APP_NAME: str = "AI Vocabulary Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Spaced Repetition (SM-2 defaults)
    SM2_INITIAL_INTERVAL: int = 1  # days
    SM2_INITIAL_EASE: float = 2.5

    # Review scheduling
    DAILY_REVIEW_HOUR: int = 9  # 9 AM
    DAILY_REVIEW_MINUTE: int = 0

    # Audio (TTS)
    TTS_ENABLED: bool = True
    TTS_VOICE: str = "alloy"  # or other Qwen TTS voices

    # Trusted news domains for Tavily search
    TRUSTED_DOMAINS: list = Field(default_factory=lambda: [
        "reuters.com",
        "bbc.com",
        "apnews.com",
        "theguardian.com",
        "npr.org",
        "nytimes.com",
        "economist.com",
        "cnn.com",
        "washingtonpost.com",
        "ft.com",
    ])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_sqlite_url(cls, value: str) -> str:
        """Resolve relative SQLite paths from the project root."""
        if not isinstance(value, str) or not value.startswith("sqlite:///"):
            return value

        db_path = value.replace("sqlite:///", "", 1)
        if db_path == ":memory:":
            return value

        path = Path(db_path)
        if path.is_absolute():
            return value

        return f"sqlite:///{(PROJECT_ROOT / path).resolve()}"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
