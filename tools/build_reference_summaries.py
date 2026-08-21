"""Create compact manifest-derived suite summaries where no legacy suite existed."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    missing: list[str] = []
    for manifest_path in (ROOT / "benchmarks").glob("*/manifest.json"):
        target = manifest_path.parent / "references" / "suite_summary.json"
        if target.exists():
            continue
        if args.check:
            missing.append(target.relative_to(ROOT).as_posix())
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        counts = Counter(case["status"] for case in manifest["cases"])
        payload = {
            "schema_version": 1,
            "status": "FAIL" if counts["FAIL"] else "PARTIAL" if counts["BLOCKED"] or counts["NOT_RUN"] else "PASS",
            "source": "manifest aggregation backed by case reference checksums",
            "counts": dict(sorted(counts.items())),
            "cases": [
                {"id": case["id"], "slug": case["slug"], "status": case["status"], "reference": case["reference"]}
                for case in manifest["cases"]
            ],
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for path in missing:
        print(f"missing reference summary: {path}")
    return bool(missing)


if __name__ == "__main__":
    raise SystemExit(main())
