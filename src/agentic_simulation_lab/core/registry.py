from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import project_root
from .result_contract import CANONICAL_RESULT_FILE
from .status import VALID_STATUSES


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Case:
    domain: str
    slug: str
    title: str
    entrypoint: str
    status: str
    role: str = "benchmark"
    evidence: str | None = None
    id: str | None = None
    solver: str = "unspecified"
    analysis: str = "unspecified"
    reference: str | None = None
    expected_artifacts: list[str] | None = None
    result_file: str = CANONICAL_RESULT_FILE
    result_format: str = "v1"
    timeout_seconds: int = 900


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "domain", "title", "cases"}
    missing = required - data.keys()
    if missing:
        raise ManifestError(f"{path}: missing {sorted(missing)}")
    if data["schema_version"] not in {1, 2}:
        raise ManifestError(f"{path}: unsupported schema_version {data['schema_version']!r}")
    if not isinstance(data["cases"], list):
        raise ManifestError(f"{path}: cases must be a list")
    seen: set[str] = set()
    for case in data["cases"]:
        for field in ("slug", "title", "entrypoint", "status", "solver", "analysis"):
            if not case.get(field):
                raise ManifestError(f"{path}: case missing {field}")
        if case["slug"] in seen:
            raise ManifestError(f"{path}: duplicate slug {case['slug']}")
        seen.add(case["slug"])
        if case["status"] not in VALID_STATUSES:
            raise ManifestError(f"{path}: invalid status {case['status']}")
        result_file = case.get("result_file", CANONICAL_RESULT_FILE)
        if not isinstance(result_file, str) or not result_file or Path(result_file).is_absolute() or ".." in Path(result_file).parts:
            raise ManifestError(f"{path}: invalid result_file {result_file!r}")
        if case.get("result_format", "v1") not in {"v1", "legacy"}:
            raise ManifestError(f"{path}: invalid result_format {case.get('result_format')!r}")
        timeout = case.get("timeout_seconds", 900)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            raise ManifestError(f"{path}: timeout_seconds must be a positive integer")
        if data["schema_version"] >= 2 and case.get("role", "benchmark") != "utility" and "result_file" not in case:
            raise ManifestError(f"{path}: schema v2 executable case missing result_file")
    return data


def manifests(root: Path | None = None) -> Iterable[tuple[Path, dict[str, Any]]]:
    base = (root or project_root()) / "benchmarks"
    for path in sorted(base.glob("*/manifest.json")):
        yield path, load_manifest(path)


def cases(root: Path | None = None, domain: str | None = None) -> list[Case]:
    result: list[Case] = []
    for _, manifest in manifests(root):
        if domain and manifest["domain"] != domain:
            continue
        result.extend(Case(domain=manifest["domain"], **item) for item in manifest["cases"])
    return result


def find_case(domain: str, slug: str, root: Path | None = None) -> Case:
    for case in cases(root, domain):
        if case.slug == slug:
            return case
    raise KeyError(f"unknown case: {domain}/{slug}")
