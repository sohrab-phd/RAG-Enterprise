"""Document processing exceptions."""


class ProcessingError(Exception):
    """Base class for processing failures."""

    code: str = "unknown_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EmptyContentError(ProcessingError):
    code = "empty_content"


class EncryptedPdfError(ProcessingError):
    code = "encrypted_pdf"


class UnsupportedFormatError(ProcessingError):
    code = "unsupported_format"


class CorruptFileError(ProcessingError):
    code = "corrupt_file"
