"""Normalize public reference status fields while preserving original detail."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(value: object) -> str:
    text = str(value or "").upper()
    if text.startswith("PASS WITH"):
        return "PARTIAL"
    if "BLOCK" in text:
        return "BLOCKED"
    if text.startswith("PASS"):
        return "PASS"
    if text.startswith("FAIL"):
        return "FAIL"
    if "PARTIAL" in text:
        return "PARTIAL"
    return "NOT_RUN"


def visit(value: object) -> object:
    if isinstance(value, list):
        return [visit(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: visit(item) for key, item in value.items()}
    original = value.get("status")
    if isinstance(original, str):
        replacement = normalized(original)
        result["status"] = replacement
        if replacement != original:
            result.setdefault("status_detail", original)
    return result


def main() -> None:
    for path in (ROOT / "benchmarks").glob("*/references/*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps(visit(data), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
