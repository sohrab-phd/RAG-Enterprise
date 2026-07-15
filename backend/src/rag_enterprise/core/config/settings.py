"""Pydantic-based settings with environment variable support."""

from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field, RedisDsn, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_enterprise.core.config.database import DatabaseSettings


def _coerce_llm_backend(value: object) -> object:
    """Accept legacy echo/http and map to mock/api before Literal check."""
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower()
    if normalized == "echo":
        return "mock"
    if normalized == "http":
        return "api"
    return normalized


LlmBackendField = Annotated[
    Literal["local", "api", "mock"],
    BeforeValidator(_coerce_llm_backend),
    Field(default="local", validation_alias="LLM_BACKEND"),
]


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

    # Embeddings / retrieval — production default matches RC2.3–RC2.5 benchmarks
    embedding_backend: Literal["deterministic", "flag", "sentence_transformers"] = Field(
        default="sentence_transformers",
        validation_alias="EMBEDDING_BACKEND",
    )
    embedding_model_key: str = Field(
        default="BAAI/bge-m3",
        validation_alias="EMBEDDING_MODEL_KEY",
    )
    embedding_dimensions: int = Field(default=1024, validation_alias="EMBEDDING_DIMENSIONS")
    embedding_batch_size: int = Field(default=32, validation_alias="EMBEDDING_BATCH_SIZE")
    retrieval_default_top_k: int = Field(default=8, validation_alias="RETRIEVAL_DEFAULT_TOP_K")

    # LLM / generation (RC2.6: local | api | mock)
    llm_backend: LlmBackendField
    local_provider: Literal["ollama"] = Field(
        default="ollama",
        validation_alias="LOCAL_PROVIDER",
    )
    api_provider: Literal["openai"] = Field(
        default="openai",
        validation_alias="API_PROVIDER",
    )
    mock_provider: Literal["echo"] = Field(
        default="echo",
        validation_alias="MOCK_PROVIDER",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    # Legacy aliases retained for migration (prefer OPENAI_*).
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model_key: str = Field(default="auto", validation_alias="LLM_MODEL_KEY")
    llm_timeout_seconds: float = Field(default=60.0, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_legacy_backend: str | None = Field(default=None, exclude=True)
    generation_min_evidence_score: float = Field(
        default=0.25,
        validation_alias="GENERATION_MIN_EVIDENCE_SCORE",
    )
    generation_max_history_messages: int = Field(
        default=6,
        ge=5,
        le=10,
        validation_alias="GENERATION_MAX_HISTORY_MESSAGES",
    )

    # Offline evaluation artifacts (Feature 007 filesystem root)
    evaluation_storage_root: str = Field(
        default="eval-artifacts",
        validation_alias="EVALUATION_STORAGE_ROOT",
    )

    # Local upload binary storage (RC1.6)
    file_storage_root: str = Field(
        default="storage/uploads",
        validation_alias="FILE_STORAGE_ROOT",
    )

    # Upload limits (ops-validated at startup; defaults match knowledge constants)
    upload_max_file_size_bytes: int = Field(
        default=50 * 1024 * 1024,
        validation_alias="UPLOAD_MAX_FILE_SIZE_BYTES",
    )
    upload_max_bulk_files: int = Field(
        default=100,
        validation_alias="UPLOAD_MAX_BULK_FILES",
    )
    upload_session_ttl_hours: int = Field(
        default=24,
        validation_alias="UPLOAD_SESSION_TTL_HOURS",
    )

    @model_validator(mode="before")
    @classmethod
    def assemble_database_settings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        data = cls._normalize_llm_settings(data)

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

    @staticmethod
    def _normalize_llm_settings(data: dict[str, Any]) -> dict[str, Any]:
        """Map legacy echo/http and LLM_* API aliases into the RC2.6 shape."""
        backend_raw = data.get("llm_backend", data.get("LLM_BACKEND"))
        if isinstance(backend_raw, str):
            normalized = backend_raw.strip().lower()
            if normalized == "echo":
                data["llm_backend"] = "mock"
                data["llm_legacy_backend"] = "echo"
            elif normalized == "http":
                data["llm_backend"] = "api"
                data["llm_legacy_backend"] = "http"
            else:
                data["llm_backend"] = normalized

        openai_base = data.get("openai_base_url", data.get("OPENAI_BASE_URL"))
        legacy_base = data.get("llm_base_url", data.get("LLM_BASE_URL"))
        if not (isinstance(openai_base, str) and openai_base.strip()) and isinstance(
            legacy_base, str
        ):
            data["openai_base_url"] = legacy_base

        openai_key = data.get("openai_api_key", data.get("OPENAI_API_KEY"))
        legacy_key = data.get("llm_api_key", data.get("LLM_API_KEY"))
        if not (isinstance(openai_key, str) and openai_key.strip()) and isinstance(legacy_key, str):
            data["openai_api_key"] = legacy_key

        # Empty LLM_MODEL_KEY is equivalent to auto (RC2.7 local selection).
        model_raw = data.get("llm_model_key", data.get("LLM_MODEL_KEY"))
        if model_raw is None or (isinstance(model_raw, str) and not model_raw.strip()):
            data["llm_model_key"] = "auto"

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
    def llm_provider_name(self) -> str:
        """Active concrete provider for the selected backend."""
        if self.llm_backend == "local":
            return self.local_provider
        if self.llm_backend == "api":
            return self.api_provider
        return self.mock_provider

    @property
    def resolved_openai_base_url(self) -> str | None:
        value = (self.openai_base_url or self.llm_base_url or "").strip()
        return value or None

    @property
    def resolved_openai_api_key(self) -> str | None:
        value = (self.openai_api_key or self.llm_api_key or "").strip()
        return value or None

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
