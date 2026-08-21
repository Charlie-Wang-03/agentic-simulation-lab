"""Publication policy helpers shared by release tooling and tests."""

from __future__ import annotations


def evidence_integrity_gate(
    qualifications: list[dict[str, object]], errors: list[str]
) -> dict[str, object]:
    """Keep truthful case outcomes visible while gating evidence integrity."""
    return {
        "status": "PASS" if not errors else "FAIL",
        "qualifications": qualifications,
        "errors": errors,
    }
