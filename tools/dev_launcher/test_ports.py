"""Unit tests for Windows-aware port helpers."""

from __future__ import annotations

from tools.dev_launcher.ports import port_in_ranges


def test_port_in_ranges_hit() -> None:
    assert port_in_ranges(8000, [(7920, 8019), (8020, 8119)]) == (7920, 8019)


def test_port_in_ranges_miss() -> None:
    assert port_in_ranges(8300, [(7920, 8019), (8020, 8119)]) is None
