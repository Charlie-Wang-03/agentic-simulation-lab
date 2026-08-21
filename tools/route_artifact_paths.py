"""One-time mechanical rewrite that makes legacy case outputs CLI-routable."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLACEMENTS = {
    'ROOT / "outputs"': 'Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs"))',
    'PROJECT_DIR / "outputs"': 'Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", PROJECT_DIR / "outputs"))',
    'ROOT / "logs"': 'Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs"))',
    'PROJECT_DIR / "logs"': 'Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", PROJECT_DIR / "logs"))',
}


def main() -> None:
    for path in (ROOT / "benchmarks").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in REPLACEMENTS.items():
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
