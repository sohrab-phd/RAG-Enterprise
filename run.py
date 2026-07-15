#!/usr/bin/env python3
"""Single-command developer launcher for RAG-enterprise.

Usage (from repository root):

    uv run python run.py
    python run.py

Starts Docker (Postgres/Redis), runs Alembic, backend, and frontend.
Press Ctrl+C to stop app processes and run ``docker compose down``
(without ``--volumes``).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dev_launcher.launcher import main


if __name__ == "__main__":
    raise SystemExit(main())
