"""
Configuration settings for Leads microservice.

Uses pydantic-settings for environment variable loading.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://codegraph:postgres@localhost:5432/codegraph_leads",
        alias="DATABASE_URL",
    )

    # API Authentication
    leads_api_key: str = Field(default="", alias="LEADS_API_KEY")

    # Email (SMTP)
    smtp_host: str = Field(default="smtp.yandex.ru", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@codegraph.ru", alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    admin_email: str = Field(default="", alias="ADMIN_EMAIL")

    # Telegram
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    # CORS
    cors_allowed_origins: str = Field(
        default="https://codegraph.ru,https://www.codegraph.ru",
        alias="CORS_ALLOWED_ORIGINS",
    )

    # Rate Limiting
    rate_limit_leads_create: str = Field(default="10/minute", alias="RATE_LIMIT_LEADS_CREATE")

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.cors_allowed_origins:
            if self.is_production:
                return ["https://codegraph.ru", "https://www.codegraph.ru"]
            return [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "file://",
            ]
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def email_enabled(self) -> bool:
        """Check if email notifications are configured."""
        return bool(self.smtp_user and self.smtp_password and self.admin_email)

    @property
    def telegram_enabled(self) -> bool:
        """Check if Telegram notifications are configured."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
