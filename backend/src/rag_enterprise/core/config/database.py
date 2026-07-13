"""Database configuration settings."""

from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    """Database connection and pool settings."""

    url: str | None = None
    host: str = "localhost"
    port: int = 5432
    user: str = "rag"
    password: str = "rag_dev_password"
    name: str = "rag_enterprise"
    test_url: str | None = None

    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False

    def resolved_url(self) -> str:
        """Return the async SQLAlchemy database URL."""
        if self.url:
            return self._ensure_async_driver(self.url)
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )

    def resolved_test_url(self) -> str:
        """Return the async SQLAlchemy URL for tests."""
        if self.test_url:
            return self._ensure_async_driver(self.test_url)
        return "sqlite+aiosqlite:///:memory:"

    @staticmethod
    def _ensure_async_driver(url: str) -> str:
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
