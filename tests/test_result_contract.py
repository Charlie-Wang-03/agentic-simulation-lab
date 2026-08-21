import subprocess
from pathlib import Path

import pytest

from agentic_simulation_lab.core import execution
from agentic_simulation_lab.core.registry import Case


def _case(slug: str, *, timeout: int = 30) -> Case:
    return Case(
        domain="test", slug=slug, title=slug, entrypoint=f"{slug}.py", status="NOT_RUN",
        solver="Python", analysis="contract test", timeout_seconds=timeout,
    )


def _script(root: Path, case: Case, status: str, *, exit_code: int = 0, supporting_status: str | None = None) -> None:
    supporting = ""
    if supporting_status:
        supporting = f"(out / 'supporting.json').write_text(json.dumps({{'status': '{supporting_status}'}}))"
    payload = {
        "schema_version": 1, "status": status, "checks": [], "metrics": {},
        "artifacts": [], "provenance": {"test": True},
    }
    (root / case.entrypoint).write_text(
        "import json, os\nfrom pathlib import Path\n"
        "out = Path(os.environ['AGENTIC_SIM_OUTPUT_DIR'])\n"
        f"{supporting}\n"
        f"Path(os.environ['AGENTIC_SIM_RESULT_FILE']).write_text(json.dumps({payload!r}))\n"
        f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )


@pytest.fixture
def isolated_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(execution, "project_root", lambda: tmp_path)
    monkeypatch.setattr(execution, "artifacts_root", lambda root: root / "artifacts")
    return tmp_path


@pytest.mark.parametrize("status", ["PASS", "FAIL", "BLOCKED", "PARTIAL", "NOT_RUN"])
def test_authoritative_statuses(isolated_execution, status):
    case = _case(status.lower())
    _script(isolated_execution, case, status)
    record = execution.execute(case)
    assert record["physics_status"] == status
    assert record["status"] == status


def test_process_failure_overrides_physics_pass(isolated_execution):
    case = _case("process-failure")
    _script(isolated_execution, case, "PASS", exit_code=3)
    record = execution.execute(case)
    assert record["physics_status"] == "PASS"
    assert record["process_status"] == "FAIL"
    assert record["status"] == "FAIL"


def test_declared_legacy_result_is_normalized(isolated_execution):
    case = Case(
        domain="test", slug="legacy", title="legacy", entrypoint="legacy.py", status="NOT_RUN",
        solver="Python", analysis="contract test", result_file="legacy/result.json", result_format="legacy",
    )
    (isolated_execution / case.entrypoint).write_text(
        "import json, os\nfrom pathlib import Path\n"
        "path = Path(os.environ['AGENTIC_SIM_RESULT_FILE'])\npath.parent.mkdir(parents=True)\n"
        "path.write_text(json.dumps({'status': 'BLOCKED BY CURRENT API', 'files': {'log': 'run.log'}}))\n",
        encoding="utf-8",
    )
    record = execution.execute(case)
    assert record["status"] == "BLOCKED"
    assert record["result"]["schema_version"] == 1
    assert record["result"]["artifacts"] == ["run.log"]


def test_unrelated_json_cannot_override_authoritative_result(isolated_execution):
    case = _case("supporting-json")
    _script(isolated_execution, case, "FAIL", supporting_status="PASS")
    record = execution.execute(case)
    assert record["physics_status"] == "FAIL"
    assert record["status"] == "FAIL"


@pytest.mark.parametrize("body", [None, "not json", "{}"])
def test_missing_or_malformed_authoritative_result(isolated_execution, body):
    case = _case("bad-" + str(body).replace(" ", "-"))
    source = "raise SystemExit(0)\n"
    if body is not None:
        source = (
            "import os\nfrom pathlib import Path\n"
            f"Path(os.environ['AGENTIC_SIM_RESULT_FILE']).write_text({body!r})\n"
        )
    (isolated_execution / case.entrypoint).write_text(source, encoding="utf-8")
    record = execution.execute(case)
    assert record["status"] == "FAIL"
    assert record["physics_status"] is None
    assert record["result_error"]


def test_timeout_records_explicit_evidence(isolated_execution, monkeypatch):
    case = _case("timeout", timeout=7)
    (isolated_execution / case.entrypoint).write_text("pass\n", encoding="utf-8")

    def expire(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output=b"out", stderr=b"err")

    monkeypatch.setattr(execution.subprocess, "run", expire)
    record = execution.execute(case)
    assert record["status"] == "FAIL"
    assert record["process_status"] == "TIMEOUT"
    assert record["timeout_seconds"] == 7
    assert "7 second" in record["error"]


def test_dry_run_is_not_run_and_honors_override(isolated_execution):
    case = _case("dry-run", timeout=30)
    record = execution.execute(case, dry_run=True, timeout_seconds=12)
    assert record["status"] == "NOT_RUN"
    assert record["timeout_seconds"] == 12
    assert not (isolated_execution / "artifacts").exists()
