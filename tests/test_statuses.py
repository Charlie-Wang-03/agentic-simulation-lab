from agentic_simulation_lab.core.registry import cases
from agentic_simulation_lab.core.status import VALID_STATUSES


def test_status_vocabulary_is_normalized():
    assert {case.status for case in cases()} <= VALID_STATUSES


def test_historical_failures_and_blocks_are_preserved():
    statuses = {case.status for case in cases()}
    assert "FAIL" in statuses
    assert "BLOCKED" in statuses
