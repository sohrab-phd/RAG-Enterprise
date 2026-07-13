"""Shared validation helpers for knowledge commands."""

from __future__ import annotations

import re

from rag_enterprise.knowledge.constants import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_METADATA_BYTES,
    MAX_NAME_LENGTH,
    MAX_TAGS,
    MAX_TITLE_LENGTH,
)

BCP47_PATTERN = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


def is_valid_language_code(value: str) -> bool:
    return bool(BCP47_PATTERN.match(value))


def is_valid_name(value: str) -> bool:
    stripped = value.strip()
    return 0 < len(stripped) <= MAX_NAME_LENGTH


def is_valid_title(value: str) -> bool:
    stripped = value.strip()
    return 0 < len(stripped) <= MAX_TITLE_LENGTH


def is_allowed_file(file_name: str, file_size_bytes: int) -> bool:
    if file_size_bytes <= 0 or file_size_bytes > MAX_FILE_SIZE_BYTES:
        return False
    extension = "." + file_name.rsplit(".", maxsplit=1)[-1].lower() if "." in file_name else ""
    return extension in ALLOWED_EXTENSIONS


def is_valid_tags(tags: list[str]) -> bool:
    return len(tags) <= MAX_TAGS and all(tag.strip() for tag in tags)


def metadata_size_ok(metadata: dict[str, object]) -> bool:
    import json

    return len(json.dumps(metadata, separators=(",", ":"))) <= MAX_METADATA_BYTES
