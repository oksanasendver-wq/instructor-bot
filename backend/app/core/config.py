"""Конфигурация приложения"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""

    # Файл ищется относительно backend, а не текущей директории процесса.
    # Это важно для pytest/uvicorn, запущенных из корня репозитория.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str = Field(min_length=32)
    TELEGRAM_BOT_TOKEN: str
    # Optional secret supplied to Telegram when configuring the webhook.
    TELEGRAM_WEBHOOK_SECRET: str | None = None
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = Field(min_length=8)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # AI Provider
    AI_PROVIDER: Literal["groq", "nvidia"] = "groq"
    GROQ_API_KEY: str | None = None
    NVIDIA_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    NVIDIA_MODEL: str = "meta/llama-3.3-70b-instruct"

    # CORS
    FRONTEND_MINI_APP_URL: str
    FRONTEND_ADMIN_URL: str

    # Application
    TIMEZONE: str = "Asia/Almaty"
    ARRIVAL_MINUTES_BEFORE: int = Field(default=30, ge=0, le=240)
    PROFILE_MINUTES_AFTER: int = Field(default=60, ge=0, le=1440)
    REPORT_EDIT_MINUTES: int = Field(default=30, ge=1, le=1440)
    ENABLE_DEBUG: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Приводит URL Render/PostgreSQL к async-драйверу SQLAlchemy."""
        if not isinstance(value, str):
            return value

        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg2://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @field_validator("FRONTEND_MINI_APP_URL", "FRONTEND_ADMIN_URL")
    @classmethod
    def normalize_frontend_url(cls, value: str) -> str:
        """Origin в CORS не должен содержать завершающий slash."""
        return value.rstrip("/")


settings = Settings()
