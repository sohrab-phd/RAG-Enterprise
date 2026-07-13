"""Language detection tests."""

from rag_enterprise.processing.language import detect_language


def test_detects_persian() -> None:
    text = "این یک متن فارسی است که برای آزمایش تشخیص زبان نوشته شده است."
    assert detect_language(text) == "fa"


def test_detects_english() -> None:
    text = (
        "This is an English paragraph written for language detection testing "
        "in the document processing module."
    )
    assert detect_language(text) == "en"


def test_short_text_returns_unknown() -> None:
    assert detect_language("سلام") == "unknown"
