"""Knowledge management constants."""

MAX_FOLDER_DEPTH = 20
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_BULK_UPLOAD_FILES = 100
UPLOAD_SESSION_TTL_HOURS = 24
MAX_METADATA_BYTES = 16 * 1024
MAX_TAGS = 50
MAX_NAME_LENGTH = 200
MAX_TITLE_LENGTH = 500

ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx", ".txt", ".md", ".html"})
ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "text/html",
    }
)
