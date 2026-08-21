"""Pure staged classification and sanitization for supported-path AEDT diagnosis."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

PHASES = (
    "python_pyaedt",
    "installation_discovery",
    "executable_trust",
    "version_compatibility",
    "session_startup",
    "project_design_creation",
    "minimal_solve",
    "release_cleanup",
)
VALID_PHASE_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)[A-Z]:[\\/](?:[^\s'\"]+[\\/])*[^\s'\"]+")
UNIX_USER_PATH = re.compile(r"(?i)/(?:home|Users)/(?:[^\s'\"]+[\\/])*[^\s'\"]+")
PRIVATE_HOST = re.compile(r"(?i)\b(?:LAPTOP|DESKTOP)-[A-Z0-9-]+\b")
IP_ADDRESS = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def compatibility_status(*, release: str | None, is_student: bool, secure_local: bool) -> dict[str, Any]:
    """Classify the documented secure-local transport compatibility boundary."""
    if not release:
        return {"status": "BLOCKED", "reason": "AEDT release is unknown"}
    try:
        version = tuple(int(part) for part in release.split(".", maxsplit=1))
    except (TypeError, ValueError):
        return {"status": "BLOCKED", "reason": "AEDT release is not parseable"}
    if is_student and version <= (2025, 2) and secure_local:
        return {
            "status": "BLOCKED",
            "reason": "AEDT Student 2025 R2 and earlier do not support PyAEDT default secure-local gRPC",
            "classification": "external_product_api_limitation",
            "allowed_alternative": False,
            "alternative_reason": "task policy forbids insecure/pre-service-pack transport fallback",
            "official_reference": "https://aedt.docs.pyansys.com/version/stable/Getting_started/Troubleshooting.html",
        }
    return {"status": "PASS", "reason": "no documented secure-local incompatibility matched"}


def static_ladder(
    *,
    python_version: str,
    pyaedt_version: str | None,
    module_available: bool,
    discovery: dict[str, Any],
    secure_local: bool,
) -> dict[str, Any]:
    """Build the ladder through compatibility and leave active phases NOT_RUN."""
    phases = {name: {"status": "NOT_RUN"} for name in PHASES}
    phases["python_pyaedt"] = {
        "status": "PASS" if pyaedt_version and module_available else "BLOCKED",
        "python_version": python_version,
        "pyaedt_version": pyaedt_version,
        "module_available": module_available,
    }
    phases["installation_discovery"] = {
        "status": "PASS" if discovery.get("found") else "BLOCKED",
        "observed_release": discovery.get("release"),
        "student_edition": bool(discovery.get("is_student")),
        "source": "official installation discovery",
    }
    trust = discovery.get("trust", {})
    phases["executable_trust"] = {
        "status": "PASS" if trust.get("status") == "PASS" else "BLOCKED",
        "checks": trust.get("checks", []),
    }
    prerequisites = [phases[name]["status"] for name in PHASES[:3]]
    phases["version_compatibility"] = (
        compatibility_status(
            release=discovery.get("release"),
            is_student=bool(discovery.get("is_student")),
            secure_local=secure_local,
        )
        if all(status == "PASS" for status in prerequisites)
        else {"status": "NOT_RUN", "reason": "static prerequisite did not pass"}
    )
    return finalize_ladder(phases)


def finalize_ladder(phases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return the narrowest stop stage without inferring later PASS states."""
    if tuple(phases) != PHASES:
        raise ValueError("diagnosis phases are missing or out of order")
    stopped = False
    narrowest = None
    for name, phase in phases.items():
        status = phase.get("status")
        if status not in VALID_PHASE_STATUSES:
            raise ValueError(f"invalid phase status for {name}: {status!r}")
        if stopped and status == "PASS" and name != "release_cleanup":
            raise ValueError(f"{name} cannot PASS after an earlier stop")
        if status in {"FAIL", "BLOCKED"} and narrowest is None:
            narrowest = name
            stopped = True
    statuses = [phase["status"] for phase in phases.values()]
    overall = "FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PASS" if all(
        status == "PASS" for status in statuses
    ) else "NOT_RUN"
    return {"status": overall, "narrowest_stage": narrowest, "phases": phases}


def sanitize_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove machine identity, absolute paths, IPs, and tracebacks from public evidence."""
    result = deepcopy(payload)

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if key.casefold() not in {"traceback", "executable", "installation_root", "host", "processes_after_close"}
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, str):
            value = WINDOWS_ABSOLUTE_PATH.sub("<redacted-path>", value)
            value = UNIX_USER_PATH.sub("<redacted-path>", value)
            value = PRIVATE_HOST.sub("<redacted-host>", value)
            value = IP_ADDRESS.sub("<redacted-address>", value)
        return value

    return clean(result)
