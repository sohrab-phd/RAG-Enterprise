"""Pydantic-based settings with environment variable support."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "RAG-enterprise"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_debug: bool = False
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database (placeholder — not wired yet)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "rag"
    postgres_password: str = "rag_dev_password"
    postgres_db: str = "rag_enterprise"
    database_url: PostgresDsn | None = None

    # Redis (placeholder — not wired yet)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: RedisDsn | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return str(self.database_url)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def resolved_redis_url(self) -> str:
        if self.redis_url:
            return str(self.redis_url)
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for dependency injection."""
    return Settings()
