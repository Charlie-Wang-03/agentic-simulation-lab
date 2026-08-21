"""Audit the candidate tree for classified and hash-pinned source provenance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_simulation_lab.core.audit import audit_source_provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="candidate tree; defaults to the source project")
    args = parser.parse_args(argv)
    target = args.root.resolve() if args.root else ROOT
    if not target.is_dir():
        print(f"target root is not a directory: {target}")
        return 2
    errors = audit_source_provenance(target)
    for error in errors:
        print(error)
    if not errors:
        print("source provenance: PASS")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
