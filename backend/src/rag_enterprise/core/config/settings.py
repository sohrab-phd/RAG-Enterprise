"""Pydantic-based settings with environment variable support."""

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, RedisDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_enterprise.core.config.database import DatabaseSettings


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

    # Database
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(default="rag", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="rag_dev_password", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_enterprise", validation_alias="POSTGRES_DB")
    database_test_url: str | None = Field(default=None, validation_alias="DATABASE_TEST_URL")
    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, validation_alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, validation_alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, validation_alias="DATABASE_POOL_RECYCLE")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Redis (placeholder — not wired yet)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url: RedisDsn | None = None

    @model_validator(mode="before")
    @classmethod
    def assemble_database_settings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if "database" in data and isinstance(data["database"], dict):
            return data

        data["database"] = DatabaseSettings(
            url=data.get("database_url") or data.get("DATABASE_URL"),
            host=data.get("postgres_host") or data.get("POSTGRES_HOST", "localhost"),
            port=int(data.get("postgres_port") or data.get("POSTGRES_PORT", 5432)),
            user=data.get("postgres_user") or data.get("POSTGRES_USER", "rag"),
            password=data.get("postgres_password")
            or data.get("POSTGRES_PASSWORD", "rag_dev_password"),
            name=data.get("postgres_db") or data.get("POSTGRES_DB", "rag_enterprise"),
            test_url=data.get("database_test_url") or data.get("DATABASE_TEST_URL"),
            pool_size=int(data.get("database_pool_size") or data.get("DATABASE_POOL_SIZE", 5)),
            max_overflow=int(
                data.get("database_max_overflow") or data.get("DATABASE_MAX_OVERFLOW", 10)
            ),
            pool_timeout=int(
                data.get("database_pool_timeout") or data.get("DATABASE_POOL_TIMEOUT", 30)
            ),
            pool_recycle=int(
                data.get("database_pool_recycle") or data.get("DATABASE_POOL_RECYCLE", 1800)
            ),
            echo=bool(data.get("database_echo") or data.get("DATABASE_ECHO", False)),
        )
        return data

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
        return self.database.resolved_url()

    @property
    def resolved_database_test_url(self) -> str:
        return self.database.resolved_test_url()

    @property
    def resolved_redis_url(self) -> str:
        if self.redis_url:
            return str(self.redis_url)
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for dependency injection."""
    return Settings()
