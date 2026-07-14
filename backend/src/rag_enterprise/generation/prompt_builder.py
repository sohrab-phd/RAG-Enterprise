"""PromptBuilder — assemble versioned grounded prompts."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from rag_enterprise.generation.exceptions import PromptTooLargeError
from rag_enterprise.generation.models import BuiltPrompt, MessageRole, MessageTurn
from rag_enterprise.generation.templates import v1
from rag_enterprise.retrieval.models import RetrievedChunk

_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")


@dataclass(frozen=True)
class PromptBuilderConfig:
    max_prompt_chars: int = 24_000
    max_history_messages: int = 6
    excerpt_chars: int = 400


class PromptBuilder:
    """Build LLM prompts from versioned templates and runtime context."""

    def __init__(self, config: PromptBuilderConfig | None = None) -> None:
        self._config = config or PromptBuilderConfig()

    @property
    def template_version(self) -> str:
        return v1.VERSION

    def detect_language(self, question: str, language_hint: str | None = None) -> str:
        if language_hint in {"fa", "en"}:
            return language_hint
        if _PERSIAN_RE.search(question):
            return "fa"
        return "en"

    def language_name(self, code: str) -> str:
        return "Persian" if code == "fa" else "English"

    def clamp_history(self, history: list[MessageTurn]) -> list[MessageTurn]:
        max_n = min(10, max(5, self._config.max_history_messages))
        filtered = [
            turn
            for turn in history
            if turn.role in {MessageRole.USER, MessageRole.ASSISTANT} and turn.content.strip()
        ]
        return filtered[-max_n:]

    def build(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[MessageTurn],
        language_hint: str | None = None,
    ) -> BuiltPrompt:
        language = self.detect_language(question, language_hint)
        language_name = self.language_name(language)
        history_used = self.clamp_history(history)
        chunks_used = list(chunks)

        while True:
            system_prompt = v1.SYSTEM_TEMPLATE.format(language_name=language_name)
            user_prompt, markers = self._compose_user_prompt(
                question=question,
                chunks=chunks_used,
                history=history_used,
                language_name=language_name,
            )
            total = len(system_prompt) + len(user_prompt)
            if total <= self._config.max_prompt_chars:
                return BuiltPrompt(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    template_version=v1.VERSION,
                    markers=markers,
                    chunks_used=chunks_used,
                    history_used=history_used,
                )
            if history_used:
                history_used = history_used[1:]
                continue
            if len(chunks_used) > 1:
                chunks_used = chunks_used[:-1]
                continue
            raise PromptTooLargeError()

    def _compose_user_prompt(
        self,
        *,
        question: str,
        chunks: list[RetrievedChunk],
        history: list[MessageTurn],
        language_name: str,
    ) -> tuple[str, dict[str, uuid.UUID]]:
        markers: dict[str, uuid.UUID] = {}
        parts: list[str] = []

        if history:
            parts.append(v1.HISTORY_HEADER)
            for turn in history:
                parts.append(f"{turn.role.value}: {turn.content.strip()}")
            parts.append("")

        parts.append(v1.EVIDENCE_HEADER)
        for index, chunk in enumerate(chunks, start=1):
            marker = str(index)
            markers[marker] = chunk.chunk_id
            text = chunk.text.strip()
            if len(text) > self._config.excerpt_chars * 4:
                text = text[: self._config.excerpt_chars * 4] + "…"
            parts.append(
                v1.CHUNK_FORMAT.format(
                    marker=marker,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    heading=chunk.heading or "(none)",
                    text=text,
                ).rstrip()
            )
        parts.append("")
        parts.append(v1.QUESTION_HEADER)
        parts.append(question.strip())
        parts.append("")
        parts.append(v1.OUTPUT_RULES.format(language_name=language_name))
        return "\n".join(parts), markers
