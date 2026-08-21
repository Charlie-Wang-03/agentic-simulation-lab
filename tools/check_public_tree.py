from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_simulation_lab.core.audit import audit, audit_export, audit_release_metadata, audit_source_provenance
from agentic_simulation_lab.core.validation import validate_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="audit a source or exported public tree")
    parser.add_argument("--root", type=Path, help="exported tree to audit; defaults to the source project")
    args = parser.parse_args(argv)
    target = args.root.resolve() if args.root else ROOT
    if not target.is_dir():
        print(f"target root is not a directory: {target}")
        return 2
    errors = validate_project(target) + (
        audit_export(target)
        if args.root
        else audit(target) + audit_source_provenance(target) + audit_release_metadata(target)
    )
    for error in errors:
        print(error)
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
