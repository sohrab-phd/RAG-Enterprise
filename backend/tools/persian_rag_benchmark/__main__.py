"""Allow ``python -m tools.persian_rag_benchmark`` from the backend directory."""

from __future__ import annotations

from tools.persian_rag_benchmark.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
