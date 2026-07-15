"""Regression tests for Vite Local URL parsing (ANSI-aware)."""

from __future__ import annotations

from tools.dev_launcher.launcher import _extract_vite_url


def test_extract_vite_url_strips_ansi_around_local_label() -> None:
    # Vite colors "Local" and the URL; without stripping, Local: is non-contiguous.
    line = (
        "  \x1b[32m➜\x1b[39m  \x1b[1mLocal\x1b[22m:   "
        "\x1b[36mhttp://127.0.0.1:5173/\x1b[39m"
    )
    assert _extract_vite_url([line], "") == "http://127.0.0.1:5173"


def test_extract_vite_url_plain_line() -> None:
    assert (
        _extract_vite_url(["  ➜  Local:   http://127.0.0.1:5173/"], "")
        == "http://127.0.0.1:5173"
    )


def test_extract_vite_url_fallback() -> None:
    assert _extract_vite_url(["ready in 372 ms"], "http://localhost:5173") == (
        "http://localhost:5173"
    )
