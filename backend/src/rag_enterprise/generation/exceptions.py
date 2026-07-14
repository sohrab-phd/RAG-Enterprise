"""Generation domain exceptions."""

from __future__ import annotations


class GenerationError(Exception):
    """Base generation error with a stable failure code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class InvalidQuestionError(GenerationError):
    def __init__(self, message: str = "Question text is empty") -> None:
        super().__init__("invalid_question", message)


class PromptTooLargeError(GenerationError):
    def __init__(self, message: str = "Prompt exceeds size budget after truncation") -> None:
        super().__init__("prompt_too_large", message)


class ModelUnavailableError(GenerationError):
    def __init__(self, message: str) -> None:
        super().__init__("model_unavailable", message)


class GenerationTimeoutError(GenerationError):
    def __init__(self, message: str = "LLM completion timed out") -> None:
        super().__init__("generation_timeout", message)
