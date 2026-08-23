import pytest

from agentic_simulation_lab.core.release_policy import (
    ACCEPTED_RESIDUAL_RISK_OUTCOME,
    evidence_integrity_gate,
    publication_decision_gate,
)


def test_truthful_case_outcomes_are_qualifications_not_gate_failures():
    qualifications = [
        {"case": "reactive-cht", "observed_status": "FAIL"},
        {"case": "electrostatic-current", "observed_status": "BLOCKED"},
        {"case": "connect", "observed_status": "NOT_RUN"},
    ]

    gate = evidence_integrity_gate(qualifications, [])

    assert gate["status"] == "PASS"
    assert [item["observed_status"] for item in gate["qualifications"]] == [
        "FAIL",
        "BLOCKED",
        "NOT_RUN",
    ]


def test_evidence_integrity_error_blocks_publication_without_rewriting_status():
    qualifications = [{"case": "reactive-cht", "observed_status": "FAIL"}]

    gate = evidence_integrity_gate(qualifications, ["threshold evidence is inconsistent"])

    assert gate["status"] == "FAIL"
    assert gate["qualifications"][0]["observed_status"] == "FAIL"


@pytest.mark.parametrize(
    ("legal_status", "decision", "expected_status"),
    [
        ("CLEARED", "APPROVED", "PASS"),
        ("CLEARED", "NOT_APPROVED", "FAIL"),
        ("LEGAL_REVIEW_REQUIRED", "APPROVED", "FAIL"),
        ("LEGAL_REVIEW_REQUIRED", "NOT_APPROVED", "FAIL"),
        ("BLOCKED", "APPROVED", "FAIL"),
        ("BLOCKED", "APPROVED_WITH_RESIDUAL_RISK", "FAIL"),
        ("BLOCKED", "NOT_APPROVED", "FAIL"),
    ],
)
def test_publication_decision_gate_is_fail_closed(legal_status, decision, expected_status):
    gate = publication_decision_gate({"corpus": legal_status}, {"corpus": decision})

    assert gate["status"] == expected_status


def test_residual_risk_approval_passes_with_visible_legal_warning():
    gate = publication_decision_gate(
        {"corpus": "LEGAL_REVIEW_REQUIRED"},
        {"corpus": "APPROVED_WITH_RESIDUAL_RISK"},
    )

    assert gate["status"] == "PASS"
    assert gate["outcome"] == ACCEPTED_RESIDUAL_RISK_OUTCOME
    assert gate["warnings"]
    assert gate["items"][0]["legal_evidence_status"] == "LEGAL_REVIEW_REQUIRED"
