from __future__ import annotations

import json
from pathlib import Path

from .registry import manifests


def validate_project(root: Path) -> list[str]:
    errors: list[str] = []
    expected = 11
    found = list(manifests(root))
    if len(found) != expected:
        errors.append(f"expected {expected} manifests, found {len(found)}")
    for path, manifest in found:
        for case in manifest["cases"]:
            if not (root / case["entrypoint"]).is_file():
                errors.append(f"{path}: missing {case['entrypoint']}")
            evidence = case.get("evidence")
            if evidence:
                evidence_path = root / evidence
                if not evidence_path.is_file():
                    errors.append(f"{path}: missing evidence {evidence}")
                else:
                    if evidence_path.stat().st_size >= 1_000_000:
                        errors.append(f"{path}: reference exceeds 1 MB: {evidence}")
                    try:
                        json.loads(evidence_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                        errors.append(f"{path}: invalid reference {evidence}: {exc}")
    catalog_path = root / "benchmarks" / "catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog_domains = {item["domain"]: item["cases"] for item in catalog["domains"]}
        for _, manifest in found:
            if catalog_domains.get(manifest["domain"]) != manifest["cases"]:
                errors.append(f"catalog is stale for {manifest['domain']}")
    except (OSError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid catalog: {exc}")
    return errors
