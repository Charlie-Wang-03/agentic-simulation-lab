from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_simulation_lab.core.registry import manifests


def build(root: Path = ROOT) -> dict[str, object]:
    domains = []
    for path, manifest in manifests(root):
        domains.append({
            "domain": manifest["domain"], "title": manifest["title"],
            "manifest": path.relative_to(root).as_posix(), "cases": manifest["cases"],
        })
    return {"schema_version": 1, "project": "agentic-simulation-lab", "domains": domains}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "benchmarks" / "catalog.json"
    rendered = json.dumps(build(), indent=2) + "\n"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != rendered:
            print("catalog.json is stale", file=sys.stderr)
            return 1
        return 0
    target.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
