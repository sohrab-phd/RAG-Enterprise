"""PromptBuilder — assemble versioned grounded prompts."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from rag_enterprise.generation.context_assembly import (
    ContextAssemblyResult,
    ContextBlock,
    assemble_context,
)
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
        assembly = assemble_context(chunks)
        blocks = list(assembly.blocks)

        while True:
            system_prompt = v1.SYSTEM_TEMPLATE.format(language_name=language_name)
            user_prompt, markers, chunks_used = self._compose_user_prompt(
                question=question,
                blocks=blocks,
                history=history_used,
                language_name=language_name,
            )
            total = len(system_prompt) + len(user_prompt)
            if total <= self._config.max_prompt_chars:
                diagnostics = self._diagnostics_with_prompt(
                    assembly=assembly,
                    blocks=blocks,
                    user_prompt=user_prompt,
                )
                return BuiltPrompt(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    template_version=v1.VERSION,
                    markers=markers,
                    chunks_used=chunks_used,
                    history_used=history_used,
                    context_diagnostics=diagnostics,
                )
            if history_used:
                history_used = history_used[1:]
                continue
            if len(blocks) > 1:
                # Drop lowest-score block (blocks ordered by score desc).
                blocks = blocks[:-1]
                continue
            raise PromptTooLargeError()

    def _compose_user_prompt(
        self,
        *,
        question: str,
        blocks: list[ContextBlock],
        history: list[MessageTurn],
        language_name: str,
    ) -> tuple[str, dict[str, uuid.UUID], list[RetrievedChunk]]:
        markers: dict[str, uuid.UUID] = {}
        parts: list[str] = []
        chunks_used: list[RetrievedChunk] = []
        marker_index = 0

        if history:
            parts.append(v1.HISTORY_HEADER)
            for turn in history:
                parts.append(f"{turn.role.value}: {turn.content.strip()}")
            parts.append("")

        parts.append(v1.EVIDENCE_HEADER)
        previous_heading: str | None = None
        for block in blocks:
            heading_label = (block.heading or "").strip()
            if heading_label and heading_label != previous_heading:
                parts.append(heading_label)
                previous_heading = heading_label

            marker_index += 1
            primary_marker = str(marker_index)
            markers[primary_marker] = block.primary.chunk_id
            chunks_used.append(block.primary)
            text = block.merged_text.strip()
            max_chars = self._config.excerpt_chars * 4
            if len(text) > max_chars:
                text = text[:max_chars] + "…"
            parts.append(
                v1.CHUNK_FORMAT.format(
                    marker=primary_marker,
                    chunk_id=block.primary.chunk_id,
                    document_id=block.primary.document_id,
                    heading=block.heading or "(none)",
                    text=text,
                ).rstrip()
            )

            for secondary in block.chunks:
                if secondary.chunk_id == block.primary.chunk_id:
                    continue
                marker_index += 1
                secondary_marker = str(marker_index)
                markers[secondary_marker] = secondary.chunk_id
                chunks_used.append(secondary)
                parts.append(
                    v1.CHUNK_FORMAT.format(
                        marker=secondary_marker,
                        chunk_id=secondary.chunk_id,
                        document_id=secondary.document_id,
                        heading=secondary.heading or block.heading or "(none)",
                        text=f"[included in [{primary_marker}]]",
                    ).rstrip()
                )

        parts.append("")
        parts.append(v1.QUESTION_HEADER)
        parts.append(question.strip())
        parts.append("")
        parts.append(v1.OUTPUT_RULES.format(language_name=language_name))
        return "\n".join(parts), markers, chunks_used

    @staticmethod
    def _diagnostics_with_prompt(
        *,
        assembly: ContextAssemblyResult,
        blocks: list[ContextBlock],
        user_prompt: str,
    ) -> dict[str, object]:
        # Recompute diagnostics if size trimming dropped blocks.
        trimmed = ContextAssemblyResult(
            blocks=tuple(blocks),
            chunks_for_citations=tuple(chunk for block in blocks for chunk in block.chunks),
            original_chunk_ids=assembly.original_chunk_ids,
            duplicate_removed_ids=assembly.duplicate_removed_ids,
            duplicated_chars_removed=assembly.duplicated_chars_removed,
            context_char_count=sum(len(block.merged_text) for block in blocks),
            estimated_token_count=max(
                1,
                (sum(len(block.merged_text) for block in blocks) + 3) // 4,
            )
            if blocks
            else 0,
        )
        payload = trimmed.to_diagnostics()
        payload["final_prompt_chars"] = len(user_prompt)
        payload["evidence_prompt_chars"] = user_prompt.count("text:")  # presence signal
        return payload
