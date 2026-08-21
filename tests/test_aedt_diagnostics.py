import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "benchmarks" / "electromagnetics" / "common" / "aedt_diagnostics.py"
SPEC = importlib.util.spec_from_file_location("aedt_diagnostics", MODULE_PATH)
assert SPEC and SPEC.loader
diagnostics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostics)


def _discovery(**overrides):
    value = {
        "found": True,
        "release": "2025.2",
        "is_student": True,
        "trust": {"status": "PASS", "checks": ["local path"]},
    }
    value.update(overrides)
    return value


def test_student_2025r2_secure_local_is_documented_block():
    ladder = diagnostics.static_ladder(
        python_version="3.12.0",
        pyaedt_version="1.4.0",
        module_available=True,
        discovery=_discovery(),
        secure_local=True,
    )
    assert ladder["status"] == "BLOCKED"
    assert ladder["narrowest_stage"] == "version_compatibility"
    assert ladder["phases"]["session_startup"]["status"] == "NOT_RUN"


def test_missing_runtime_never_becomes_pass():
    ladder = diagnostics.static_ladder(
        python_version="3.10.0",
        pyaedt_version=None,
        module_available=False,
        discovery=_discovery(found=False, trust={}),
        secure_local=True,
    )
    assert ladder["status"] == "BLOCKED"
    assert ladder["narrowest_stage"] == "python_pyaedt"
    assert all(
        phase["status"] != "PASS"
        for name, phase in ladder["phases"].items()
        if name not in {"installation_discovery"}
    )


def test_pass_after_failure_is_rejected():
    phases = {name: {"status": "NOT_RUN"} for name in diagnostics.PHASES}
    phases["python_pyaedt"] = {"status": "FAIL"}
    phases["installation_discovery"] = {"status": "PASS"}
    with pytest.raises(ValueError, match="cannot PASS"):
        diagnostics.finalize_ladder(phases)


def test_public_evidence_is_sanitized():
    sanitized = diagnostics.sanitize_evidence(
        {
            "error": (
                "failed on 127.0.0.1 in "
                + "C:"
                + "\\Users\\person\\work\\case.py at LAPTOP-"
                + "SECRET"
            ),
            "traceback": "private stack",
            "runtime": {"executable": "C:\\Program Files\\solver.exe"},
        }
    )
    rendered = str(sanitized)
    assert "traceback" not in sanitized
    assert "127.0.0.1" not in rendered
    assert "person" not in rendered
    assert "LAPTOP-" + "SECRET" not in rendered
    assert "executable" not in sanitized["runtime"]
