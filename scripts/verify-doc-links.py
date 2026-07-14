"""Verify relative markdown links in RC1.5 focus docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

FOCUS_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "OVERVIEW.md",
    ROOT / "docs" / "ARCHITECTURE_SUMMARY.md",
    ROOT / "docs" / "ARCHITECTURE.md",
    ROOT / "docs" / "FEATURE_MAP.md",
    ROOT / "docs" / "DEVELOPMENT.md",
    ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md",
    ROOT / "docs" / "DEPLOYMENT.md",
    ROOT / "docs" / "EVALUATION_GUIDE.md",
    ROOT / "docs" / "DEMO_GUIDE.md",
    ROOT / "docs" / "CONTRIBUTING.md",
    ROOT / "docs" / "DECISIONS.md",
    ROOT / "docs" / "TECH_STACK.md",
    ROOT / "docs" / "ROADMAP.md",
    ROOT / "docs" / "PRD.md",
    ROOT / "backend" / "README.md",
    ROOT / "frontend" / "README.md",
    ROOT / "specs" / "README.md",
    ROOT / "demo" / "README.md",
    ROOT / "infrastructure" / "README.md",
    ROOT / "tests" / "README.md",
]


def main() -> int:
    missing: list[str] = []
    checked = 0
    for path in FOCUS_FILES:
        text = path.read_text(encoding="utf-8")
        for _label, target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part = target.split("#", 1)[0]
            if not file_part:
                continue
            resolved = (path.parent / file_part).resolve()
            checked += 1
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {target} (resolved {resolved})")
    print(f"Checked {checked} relative links")
    if missing:
        print("MISSING:")
        for item in missing:
            print(f" - {item}")
        return 1
    print("All focus relative links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
