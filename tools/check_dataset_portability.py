"""Check public reference data for machine-specific embedded metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOTS = list((ROOT / "benchmarks").glob("*/references")) + [ROOT / "references"]
PRIVATE = (
    re.compile(r"(?i)^[A-Z]:[\\/]"),
    re.compile(r"^\\\\"),
    re.compile(r"(?i)^/(Users|home)/"),
    re.compile("(?i)charlie" + "wang|LAP" + "TOP-[A-Z0-9-]+"),
)


def strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(key)
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def main() -> int:
    errors: list[str] = []
    for base in REFERENCE_ROOTS:
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: invalid JSON: {exc}")
                continue
            for value in strings(payload):
                if any(pattern.search(value) for pattern in PRIVATE):
                    errors.append(f"{path.relative_to(ROOT).as_posix()}: machine-specific metadata")
                    break
        for path in base.rglob("*.npz"):
            try:
                import numpy as np

                with np.load(path, allow_pickle=False) as archive:
                    values = [str(item) for name in archive.files for item in archive[name].ravel() if archive[name].dtype.kind in "US"]
                if any(pattern.search(value) for value in values for pattern in PRIVATE):
                    errors.append(f"{path.relative_to(ROOT).as_posix()}: machine-specific NPZ metadata")
            except (ImportError, OSError, ValueError) as exc:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: cannot validate NPZ: {exc}")
    for error in errors:
        print(error)
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
