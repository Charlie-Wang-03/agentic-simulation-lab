"""Publication policy helpers shared by release tooling and tests."""

from __future__ import annotations

LEGAL_EVIDENCE_STATUSES = {"CLEARED", "LEGAL_REVIEW_REQUIRED", "BLOCKED"}
PUBLICATION_DECISIONS = {"APPROVED", "APPROVED_WITH_RESIDUAL_RISK", "NOT_APPROVED"}
ACCEPTED_RESIDUAL_RISK_OUTCOME = "PASS WITH ACCEPTED RESIDUAL LEGAL RISK"


def evidence_integrity_gate(
    qualifications: list[dict[str, object]], errors: list[str]
) -> dict[str, object]:
    """Keep truthful case outcomes visible while gating evidence integrity."""
    return {
        "status": "PASS" if not errors else "FAIL",
        "qualifications": qualifications,
        "errors": errors,
    }


def publication_decision_gate(
    legal_statuses: dict[str, str], decisions: dict[str, str]
) -> dict[str, object]:
    """Apply the fail-closed legal-status/maintainer-decision matrix."""
    errors: list[str] = []
    warnings: list[str] = []
    items: list[dict[str, str]] = []
    for review_unit in sorted(set(legal_statuses) | set(decisions)):
        legal_status = legal_statuses.get(review_unit, "MISSING")
        decision = decisions.get(review_unit, "MISSING")
        item = {
            "review_unit": review_unit,
            "legal_evidence_status": legal_status,
            "maintainer_publication_decision": decision,
        }
        items.append(item)
        if legal_status not in LEGAL_EVIDENCE_STATUSES:
            errors.append(f"{review_unit}: invalid or missing legal/evidence status {legal_status!r}")
            continue
        if decision not in PUBLICATION_DECISIONS:
            errors.append(f"{review_unit}: invalid or missing maintainer publication decision {decision!r}")
            continue
        if legal_status == "CLEARED" and decision == "APPROVED":
            continue
        if legal_status == "LEGAL_REVIEW_REQUIRED" and decision == "APPROVED_WITH_RESIDUAL_RISK":
            warnings.append(
                f"{review_unit}: LEGAL_REVIEW_REQUIRED remains unresolved; "
                "maintainer accepted residual legal risk for this historical corpus"
            )
            continue
        errors.append(
            f"{review_unit}: publication is not permitted for "
            f"{legal_status} + {decision}"
        )
    outcome = (
        "FAIL"
        if errors
        else ACCEPTED_RESIDUAL_RISK_OUTCOME
        if warnings
        else "PASS"
    )
    return {
        "status": "FAIL" if errors else "PASS",
        "outcome": outcome,
        "items": items,
        "warnings": warnings,
        "errors": errors,
    }
