"""RC1.1 configuration startup validation tests."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.core.config.settings import Settings
from rag_enterprise.core.config.validation import (
    ConfigIssue,
    ConfigurationError,
    emit_configuration_report,
    format_configuration_report,
    validate_configuration,
)


def _database(**overrides: object) -> DatabaseSettings:
    base: dict[str, object] = {
        "url": "sqlite+aiosqlite:///:memory:",
        "host": "localhost",
        "port": 5432,
        "user": "rag",
        "password": "rag",
        "name": "rag_enterprise",
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "echo": False,
    }
    base.update(overrides)
    return DatabaseSettings.model_validate(base)


def _settings(tmp_path: Path | None = None, **overrides: object) -> Settings:
    """Build Settings without environment bleed (model_construct)."""
    eval_root = str(tmp_path / "eval") if tmp_path is not None else "eval-artifacts-test"
    values: dict[str, object] = {
        "app_name": "RAG-enterprise",
        "app_env": "test",
        "app_debug": False,
        "log_level": "INFO",
        "api_v1_prefix": "/api/v1",
        "backend_host": "0.0.0.0",
        "backend_port": 8000,
        "database_url": None,
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_user": "rag",
        "postgres_password": "rag",
        "postgres_db": "rag_enterprise",
        "database_test_url": None,
        "database_pool_size": 5,
        "database_max_overflow": 10,
        "database_pool_timeout": 30,
        "database_pool_recycle": 1800,
        "database_echo": False,
        "database": _database(),
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_url": None,
        "embedding_backend": "deterministic",
        "embedding_model_key": "BAAI/bge-m3",
        "embedding_dimensions": 1024,
        "embedding_batch_size": 32,
        "retrieval_default_top_k": 8,
        "llm_backend": "echo",
        "llm_model_key": "gpt-4o-mini",
        "llm_base_url": None,
        "llm_api_key": None,
        "llm_timeout_seconds": 60.0,
        "generation_min_evidence_score": 0.25,
        "generation_max_history_messages": 6,
        "evaluation_storage_root": eval_root,
        "upload_max_file_size_bytes": 1024,
        "upload_max_bulk_files": 10,
        "upload_session_ttl_hours": 24,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def test_valid_default_configuration(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    validate_configuration(settings)
    assert Path(settings.evaluation_storage_root).is_dir()


def test_echo_llm_does_not_require_api_key(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        llm_backend="echo",
        llm_api_key=None,
        llm_base_url=None,
    )
    validate_configuration(settings)


def test_http_llm_requires_api_key_and_base_url(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        llm_backend="http",
        llm_api_key=None,
        llm_base_url=None,
    )
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)

    report = str(exc_info.value)
    assert "[LLM]" in report
    assert "LLM_API_KEY" in report
    assert "LLM_BASE_URL" in report


def test_http_llm_accepts_key_and_base_url(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        llm_backend="http",
        llm_api_key="sk-test",
        llm_base_url="https://api.example.com/v1",
    )
    validate_configuration(settings)


def test_evaluation_directory_created_when_missing(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "artifacts"
    assert not target.exists()
    settings = _settings(evaluation_storage_root=str(target))
    validate_configuration(settings)
    assert target.is_dir()


def test_evaluation_path_must_be_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir"
    file_path.write_text("x", encoding="utf-8")
    settings = _settings(evaluation_storage_root=str(file_path))
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    assert "EVALUATION_STORAGE_ROOT" in str(exc_info.value)
    assert "not a directory" in str(exc_info.value)


def test_upload_limits_must_be_positive(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        upload_max_file_size_bytes=0,
        upload_max_bulk_files=-1,
        upload_session_ttl_hours=0,
    )
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    report = str(exc_info.value)
    assert "[Upload]" in report
    assert "UPLOAD_MAX_FILE_SIZE_BYTES" in report
    assert "UPLOAD_MAX_BULK_FILES" in report
    assert "UPLOAD_SESSION_TTL_HOURS" in report


def test_database_pool_and_port_validation(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        database=_database(
            url="postgresql+asyncpg://rag:rag@localhost:5432/rag",
            port=70000,
            pool_size=0,
            max_overflow=-2,
            pool_timeout=0,
            pool_recycle=0,
        ),
    )
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    report = str(exc_info.value)
    assert "[Database]" in report
    assert "POSTGRES_PORT" in report
    assert "DATABASE_POOL_SIZE" in report


def test_embedding_positive_bounds(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        embedding_dimensions=0,
        embedding_batch_size=0,
        retrieval_default_top_k=0,
        embedding_model_key="   ",
    )
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    report = str(exc_info.value)
    assert "[Embedding]" in report
    assert "EMBEDDING_DIMENSIONS" in report
    assert "EMBEDDING_BATCH_SIZE" in report
    assert "RETRIEVAL_DEFAULT_TOP_K" in report


def test_logging_level_must_be_valid_enum(tmp_path: Path) -> None:
    settings = _settings(tmp_path, log_level="VERBOSE")
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    assert "LOG_LEVEL" in str(exc_info.value)


def test_validator_rejects_invalid_backends_when_constructed(tmp_path: Path) -> None:
    settings = _settings(tmp_path, llm_backend="openai", embedding_backend="weird")
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    report = str(exc_info.value)
    assert "[LLM]" in report
    assert "[Embedding]" in report
    assert "LLM_BACKEND" in report
    assert "EMBEDDING_BACKEND" in report


def test_validator_rejects_invalid_app_env(tmp_path: Path) -> None:
    settings = _settings(tmp_path, app_env="local")
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings)
    assert "APP_ENV" in str(exc_info.value)


def test_grouped_report_formatting_and_emit() -> None:
    issues = [
        ConfigIssue("LLM", "API key is required", field="LLM_API_KEY"),
        ConfigIssue("Upload", "max file size must be positive", field="UPLOAD_MAX_FILE_SIZE_BYTES"),
        ConfigIssue("LLM", "base URL is required", field="LLM_BASE_URL"),
    ]
    report = format_configuration_report(issues)
    assert report.startswith("Configuration validation failed")
    assert "[LLM]" in report
    assert "[Upload]" in report
    assert report.count("Total issues: 3") == 1

    buffer = io.StringIO()
    emit_configuration_report(report, stream=buffer)
    assert buffer.getvalue() == report


def test_configuration_error_requires_issues() -> None:
    with pytest.raises(ValueError):
        ConfigurationError([])


def test_skip_creating_evaluation_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing-eval"
    settings = _settings(evaluation_storage_root=str(missing))
    with pytest.raises(ConfigurationError) as exc_info:
        validate_configuration(settings, create_evaluation_directory=False)
    assert "does not exist" in str(exc_info.value)
    assert not missing.exists()
