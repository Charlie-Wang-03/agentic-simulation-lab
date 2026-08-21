"""Export and audit a deterministic public candidate from an exact Git revision."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_simulation_lab.core.public_export import PublicExportError, export_revision, resolve_revision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD", help="exact commit-ish to export (default: HEAD)")
    parser.add_argument("--output", type=Path, help="new/empty destination under artifacts/")
    parser.add_argument("--report", type=Path, help="local JSON report path outside the exported tree")
    args = parser.parse_args(argv)
    try:
        commit = resolve_revision(ROOT, args.revision)
        output = args.output or ROOT / "artifacts" / "public-exports" / commit[:12]
        output = output if output.is_absolute() else ROOT / output
        result = export_revision(ROOT, commit, output)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report = args.report or ROOT / "artifacts" / "public-export-reports" / f"{commit[:12]}-{stamp}.json"
        report = report if report.is_absolute() else ROOT / report
        if not report.resolve().is_relative_to((ROOT / "artifacts").resolve()):
            raise PublicExportError("report must stay under the project artifacts directory")
        if report.resolve().is_relative_to(output.resolve()):
            raise PublicExportError("report must remain outside the exported tree")
        try:
            report.parent.mkdir(parents=True, exist_ok=True)
            if report.exists():
                raise PublicExportError("report path already exists")
            report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise PublicExportError(f"unable to write local export report safely: {type(exc).__name__}: {exc}") from exc
    except PublicExportError as exc:
        print(f"public export failed safely: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "files": f"{result['file_count']} files", "report": report.relative_to(ROOT).as_posix()}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
