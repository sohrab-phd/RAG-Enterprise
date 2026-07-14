"""Startup configuration validation (RC1.1).

Collects grouped, human-readable issues and fails fast before the app
accepts traffic. Does not redesign Settings or change request-time APIs.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from rag_enterprise.core.config.settings import Settings

VALID_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"})
VALID_APP_ENVS = frozenset({"development", "staging", "production", "test"})
VALID_LLM_BACKENDS = frozenset({"echo", "http"})
VALID_EMBEDDING_BACKENDS = frozenset({"deterministic", "flag"})


@dataclass(frozen=True)
class ConfigIssue:
    """One configuration problem, belonging to a named group."""

    group: str
    message: str
    field: str | None = None


class ConfigurationError(Exception):
    """Raised when startup configuration validation fails."""

    def __init__(self, issues: list[ConfigIssue]) -> None:
        if not issues:
            raise ValueError("ConfigurationError requires at least one issue")
        self.issues = list(issues)
        super().__init__(format_configuration_report(self.issues))


def format_configuration_report(issues: list[ConfigIssue]) -> str:
    """Render grouped validation issues for operators (console / logs)."""
    by_group: dict[str, list[ConfigIssue]] = defaultdict(list)
    for issue in issues:
        by_group[issue.group].append(issue)

    lines = [
        "Configuration validation failed. Fix the issues below and restart.",
        "",
    ]
    for group in sorted(by_group.keys()):
        lines.append(f"[{group}]")
        for issue in by_group[group]:
            prefix = f"{issue.field}: " if issue.field else ""
            lines.append(f"  - {prefix}{issue.message}")
        lines.append("")
    lines.append(f"Total issues: {len(issues)}")
    return "\n".join(lines).rstrip() + "\n"


def emit_configuration_report(report: str, *, stream: object | None = None) -> None:
    """Write a human-readable validation report to stderr (or a custom stream)."""
    target = stream if stream is not None else sys.stderr
    write = getattr(target, "write", None)
    if callable(write):
        write(report)
        flush = getattr(target, "flush", None)
        if callable(flush):
            flush()


def validate_configuration(
    settings: Settings,
    *,
    create_evaluation_directory: bool = True,
) -> None:
    """Validate settings for startup readiness.

    Raises:
        ConfigurationError: when one or more grouped issues are found.
    """
    issues: list[ConfigIssue] = []
    issues.extend(_validate_database(settings))
    issues.extend(_validate_llm(settings))
    issues.extend(_validate_embedding(settings))
    issues.extend(_validate_evaluation(settings, create_directory=create_evaluation_directory))
    issues.extend(_validate_file_storage(settings, create_directory=create_evaluation_directory))
    issues.extend(_validate_upload(settings))
    issues.extend(_validate_logging(settings))
    issues.extend(_validate_environment(settings))

    if issues:
        raise ConfigurationError(issues)


def _validate_database(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    db = settings.database

    if not db.host.strip():
        issues.append(
            ConfigIssue("Database", "host must be a non-empty string", field="POSTGRES_HOST")
        )
    if not (1 <= db.port <= 65535):
        issues.append(
            ConfigIssue(
                "Database",
                f"port must be between 1 and 65535 (got {db.port})",
                field="POSTGRES_PORT",
            )
        )
    if not db.user.strip():
        issues.append(
            ConfigIssue("Database", "user must be a non-empty string", field="POSTGRES_USER")
        )
    if not db.name.strip():
        issues.append(
            ConfigIssue("Database", "database name must be non-empty", field="POSTGRES_DB")
        )
    if db.pool_size <= 0:
        issues.append(
            ConfigIssue(
                "Database",
                f"pool size must be positive (got {db.pool_size})",
                field="DATABASE_POOL_SIZE",
            )
        )
    if db.max_overflow < 0:
        issues.append(
            ConfigIssue(
                "Database",
                f"max overflow must be >= 0 (got {db.max_overflow})",
                field="DATABASE_MAX_OVERFLOW",
            )
        )
    if db.pool_timeout <= 0:
        issues.append(
            ConfigIssue(
                "Database",
                f"pool timeout must be positive (got {db.pool_timeout})",
                field="DATABASE_POOL_TIMEOUT",
            )
        )
    if db.pool_recycle <= 0:
        issues.append(
            ConfigIssue(
                "Database",
                f"pool recycle must be positive (got {db.pool_recycle})",
                field="DATABASE_POOL_RECYCLE",
            )
        )

    try:
        url = settings.resolved_database_url
    except (TypeError, ValueError) as exc:
        issues.append(
            ConfigIssue(
                "Database",
                f"unable to resolve database URL ({exc})",
                field="DATABASE_URL",
            )
        )
        return issues

    if not url.strip():
        issues.append(
            ConfigIssue("Database", "resolved database URL is empty", field="DATABASE_URL")
        )
    elif not (
        url.startswith("postgresql+")
        or url.startswith("postgresql://")
        or url.startswith("sqlite+")
        or url.startswith("sqlite://")
    ):
        issues.append(
            ConfigIssue(
                "Database",
                "URL must use postgresql or sqlite with an async-capable driver "
                f"(got scheme for {url.split(':', maxsplit=1)[0]!r})",
                field="DATABASE_URL",
            )
        )

    return issues


def _validate_llm(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    backend = settings.llm_backend

    if backend not in VALID_LLM_BACKENDS:
        issues.append(
            ConfigIssue(
                "LLM",
                f"backend must be one of {sorted(VALID_LLM_BACKENDS)} (got {backend!r})",
                field="LLM_BACKEND",
            )
        )

    if not settings.llm_model_key.strip():
        issues.append(ConfigIssue("LLM", "model key must be non-empty", field="LLM_MODEL_KEY"))

    if settings.llm_timeout_seconds <= 0:
        issues.append(
            ConfigIssue(
                "LLM",
                f"timeout must be positive (got {settings.llm_timeout_seconds})",
                field="LLM_TIMEOUT_SECONDS",
            )
        )

    if not (0.0 <= settings.generation_min_evidence_score <= 1.0):
        issues.append(
            ConfigIssue(
                "LLM",
                "GENERATION_MIN_EVIDENCE_SCORE must be between 0 and 1 "
                f"(got {settings.generation_min_evidence_score})",
                field="GENERATION_MIN_EVIDENCE_SCORE",
            )
        )

    if backend == "http":
        api_key = (settings.llm_api_key or "").strip()
        if not api_key:
            issues.append(
                ConfigIssue(
                    "LLM",
                    "API key is required when LLM_BACKEND=http",
                    field="LLM_API_KEY",
                )
            )
        base_url = (settings.llm_base_url or "").strip()
        if not base_url:
            issues.append(
                ConfigIssue(
                    "LLM",
                    "base URL is required when LLM_BACKEND=http",
                    field="LLM_BASE_URL",
                )
            )
    # echo: API key intentionally optional

    return issues


def _validate_embedding(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    backend = settings.embedding_backend

    if backend not in VALID_EMBEDDING_BACKENDS:
        issues.append(
            ConfigIssue(
                "Embedding",
                f"backend must be one of {sorted(VALID_EMBEDDING_BACKENDS)} (got {backend!r})",
                field="EMBEDDING_BACKEND",
            )
        )
    if not settings.embedding_model_key.strip():
        issues.append(
            ConfigIssue(
                "Embedding",
                "model key must be non-empty",
                field="EMBEDDING_MODEL_KEY",
            )
        )
    if settings.embedding_dimensions <= 0:
        issues.append(
            ConfigIssue(
                "Embedding",
                f"dimensions must be positive (got {settings.embedding_dimensions})",
                field="EMBEDDING_DIMENSIONS",
            )
        )
    if settings.embedding_batch_size <= 0:
        issues.append(
            ConfigIssue(
                "Embedding",
                f"batch size must be positive (got {settings.embedding_batch_size})",
                field="EMBEDDING_BATCH_SIZE",
            )
        )
    if settings.retrieval_default_top_k <= 0:
        issues.append(
            ConfigIssue(
                "Embedding",
                f"default top_k must be positive (got {settings.retrieval_default_top_k})",
                field="RETRIEVAL_DEFAULT_TOP_K",
            )
        )
    return issues


def _validate_evaluation(
    settings: Settings,
    *,
    create_directory: bool,
) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    root = settings.evaluation_storage_root.strip()
    if not root:
        issues.append(
            ConfigIssue(
                "Evaluation",
                "storage root must be a non-empty path",
                field="EVALUATION_STORAGE_ROOT",
            )
        )
        return issues

    path = Path(root)
    if path.exists() and not path.is_dir():
        issues.append(
            ConfigIssue(
                "Evaluation",
                f"path exists but is not a directory: {path}",
                field="EVALUATION_STORAGE_ROOT",
            )
        )
        return issues

    if create_directory:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            issues.append(
                ConfigIssue(
                    "Evaluation",
                    f"unable to create storage directory {path}: {exc}",
                    field="EVALUATION_STORAGE_ROOT",
                )
            )
            return issues

    if not path.exists() or not path.is_dir():
        issues.append(
            ConfigIssue(
                "Evaluation",
                f"storage directory does not exist: {path}",
                field="EVALUATION_STORAGE_ROOT",
            )
        )
    return issues


def _validate_file_storage(
    settings: Settings,
    *,
    create_directory: bool,
) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    root = settings.file_storage_root.strip()
    if not root:
        issues.append(
            ConfigIssue(
                "Upload",
                "file storage root must be a non-empty path",
                field="FILE_STORAGE_ROOT",
            )
        )
        return issues

    path = Path(root)
    if path.exists() and not path.is_dir():
        issues.append(
            ConfigIssue(
                "Upload",
                f"path exists but is not a directory: {path}",
                field="FILE_STORAGE_ROOT",
            )
        )
        return issues

    if create_directory:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            issues.append(
                ConfigIssue(
                    "Upload",
                    f"unable to create storage directory {path}: {exc}",
                    field="FILE_STORAGE_ROOT",
                )
            )
            return issues

    if path.exists() and path.is_dir():
        probe = path / ".config_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            issues.append(
                ConfigIssue(
                    "Upload",
                    f"storage directory is not writable: {exc}",
                    field="FILE_STORAGE_ROOT",
                )
            )
    return issues


def _validate_upload(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    if settings.upload_max_file_size_bytes <= 0:
        issues.append(
            ConfigIssue(
                "Upload",
                f"max file size must be positive (got {settings.upload_max_file_size_bytes})",
                field="UPLOAD_MAX_FILE_SIZE_BYTES",
            )
        )
    if settings.upload_max_bulk_files <= 0:
        issues.append(
            ConfigIssue(
                "Upload",
                f"max bulk files must be positive (got {settings.upload_max_bulk_files})",
                field="UPLOAD_MAX_BULK_FILES",
            )
        )
    if settings.upload_session_ttl_hours <= 0:
        issues.append(
            ConfigIssue(
                "Upload",
                f"session TTL hours must be positive (got {settings.upload_session_ttl_hours})",
                field="UPLOAD_SESSION_TTL_HOURS",
            )
        )
    return issues


def _validate_logging(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    level = settings.log_level.strip().upper()
    if level not in VALID_LOG_LEVELS:
        issues.append(
            ConfigIssue(
                "Logging",
                f"log level must be one of {sorted(VALID_LOG_LEVELS)} (got {settings.log_level!r})",
                field="LOG_LEVEL",
            )
        )
    return issues


def _validate_environment(settings: Settings) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    if settings.app_env not in VALID_APP_ENVS:
        issues.append(
            ConfigIssue(
                "Environment",
                f"app_env must be one of {sorted(VALID_APP_ENVS)} (got {settings.app_env!r})",
                field="APP_ENV",
            )
        )
    if settings.backend_port < 1 or settings.backend_port > 65535:
        issues.append(
            ConfigIssue(
                "Environment",
                f"backend port must be between 1 and 65535 (got {settings.backend_port})",
                field="BACKEND_PORT",
            )
        )
    if not settings.api_v1_prefix.startswith("/"):
        issues.append(
            ConfigIssue(
                "Environment",
                f"api_v1_prefix must start with '/' (got {settings.api_v1_prefix!r})",
                field="API_V1_PREFIX",
            )
        )
    return issues
