from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .status import VALID_STATUSES, normalize_status

SCHEMA_VERSION = 1
CANONICAL_RESULT_FILE = "case-result.json"


class ResultContractError(ValueError):
    pass


def load_result(path: Path, *, legacy: bool = False) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ResultContractError(f"missing authoritative result: {path.name}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResultContractError(f"malformed authoritative result: {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ResultContractError("authoritative result must be a JSON object")
    if legacy:
        raw_status = payload.get("status")
        status = normalize_status(raw_status)
        if status == "NOT_RUN" and raw_status != "NOT_RUN":
            raise ResultContractError(f"legacy authoritative result has invalid status: {raw_status!r}")
        checks = payload.get("checks", [])
        if not isinstance(checks, (list, dict)):
            checks = []
        metrics = payload.get("metrics", payload.get("results", {}))
        if not isinstance(metrics, dict):
            metrics = {}
        artifacts = payload.get("artifacts", payload.get("files", []))
        if isinstance(artifacts, dict):
            artifacts = list(artifacts.values())
        elif isinstance(artifacts, str):
            artifacts = [artifacts]
        elif not isinstance(artifacts, list):
            artifacts = []
        return {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "checks": checks,
            "metrics": metrics,
            "artifacts": artifacts,
            "provenance": {"format": "legacy", "source": path.name},
        }
    required = {"schema_version", "status", "checks", "metrics", "artifacts", "provenance"}
    missing = required - payload.keys()
    if missing:
        raise ResultContractError(f"authoritative result missing fields: {sorted(missing)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ResultContractError(f"unsupported result schema_version: {payload['schema_version']!r}")
    if payload["status"] not in VALID_STATUSES:
        raise ResultContractError(f"invalid authoritative status: {payload['status']!r}")
    if not isinstance(payload["checks"], (list, dict)):
        raise ResultContractError("checks must be a list or object")
    if not isinstance(payload["metrics"], dict):
        raise ResultContractError("metrics must be an object")
    if not isinstance(payload["artifacts"], list):
        raise ResultContractError("artifacts must be a list")
    if not isinstance(payload["provenance"], dict):
        raise ResultContractError("provenance must be an object")
    return payload
