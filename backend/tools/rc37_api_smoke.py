"""RC3.7 API smoke checks for release validation."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

_DEFAULT_BASE = "http://127.0.0.1:8800/api/v1"
_WORKSPACE_ID = "018f0000-0000-7000-8000-000000000002"
_HEADERS = {
    "X-Organization-Id": "018f0000-0000-7000-8000-000000000001",
    "X-User-Id": "018f0000-0000-7000-8000-000000000003",
    "Content-Type": "application/json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--base-url", default=_DEFAULT_BASE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    with httpx.Client(timeout=120.0, trust_env=False) as client:
        rows.append(_check(client, "GET", f"{args.base_url}/live", None, {200}))
        rows.append(_check(client, "GET", f"{args.base_url}/ready", None, {200}))
        rows.append(
            _check(
                client,
                "POST",
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/retrieve",
                {
                    "query": "نام کاربری گلستان چیست؟",
                    "knowledge_base_id": args.knowledge_base_id,
                    "top_k": 5,
                    "language": "fa",
                },
                {200},
            )
        )
        rows.append(
            _check(
                client,
                "POST",
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/chat",
                {
                    "question": "نام کاربری گلستان چیست؟",
                    "knowledge_base_id": args.knowledge_base_id,
                    "language_hint": "fa",
                    "top_k": 5,
                },
                {200},
            )
        )
        rows.append(
            _check(
                client,
                "POST",
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/retrieve",
                {
                    "query": "x",
                    "knowledge_base_id": "00000000-0000-0000-0000-000000000000",
                    "top_k": 5,
                },
                {404},
            )
        )
        rows.append(
            _check(
                client,
                "POST",
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/chat",
                {"question": "", "knowledge_base_id": args.knowledge_base_id},
                {400, 422},
            )
        )
        rows.append(
            _check(
                client,
                "GET",
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/knowledge-bases/not-a-uuid",
                None,
                {422},
            )
        )
        rows.append(
            _check(
                client,
                "GET",
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/knowledge-bases/"
                "019f7108-65e7-705a-b080-e50eefd837c8",
                None,
                {200, 404},
            )
        )

    passed = sum(1 for row in rows if row["ok"])
    summary = {
        "passed": passed,
        "total": len(rows),
        "all_ok": passed == len(rows),
        "results": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "total": len(rows), "all_ok": summary["all_ok"]}))
    return 0 if summary["all_ok"] else 1


def _check(
    client: httpx.Client,
    method: str,
    url: str,
    body: dict[str, object] | None,
    expected: set[int],
) -> dict[str, object]:
    started = time.perf_counter()
    try:
        response = client.request(method, url, headers=_HEADERS, json=body)
        status = response.status_code
    except httpx.HTTPError as exc:
        status = 0
        detail = str(exc)
    else:
        detail = response.text[:200]
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "method": method,
        "url": url,
        "status": status,
        "expected": sorted(expected),
        "ok": status in expected,
        "latency_ms": latency_ms,
        "detail": detail,
    }


if __name__ == "__main__":
    raise SystemExit(main())
