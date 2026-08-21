from agentic_simulation_lab.core.release_policy import evidence_integrity_gate


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
