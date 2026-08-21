"""Dependency-free local checks used when pytest/Ruff are unavailable."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_catalog import build
from build_project_metrics import render as render_metrics

from agentic_simulation_lab.cli import main
from agentic_simulation_lab.core.audit import audit, audit_source_provenance
from agentic_simulation_lab.core.registry import cases, manifests
from agentic_simulation_lab.core.status import VALID_STATUSES
from agentic_simulation_lab.core.validation import validate_project


def run() -> None:
    loaded = list(manifests(ROOT))
    assert len(loaded) == 11
    assert all(manifest["cases"] for _, manifest in loaded)
    all_cases = cases(ROOT)
    assert len(all_cases) == 134
    assert {case.status for case in all_cases} <= VALID_STATUSES
    assert {"PASS", "FAIL", "BLOCKED", "NOT_RUN"} <= {case.status for case in all_cases}
    assert not validate_project(ROOT)
    assert not audit(ROOT)
    assert not audit_source_provenance(ROOT)
    assert build(ROOT) == json.loads((ROOT / "benchmarks" / "catalog.json").read_text(encoding="utf-8"))
    assert render_metrics(ROOT) == (ROOT / "docs" / "PROJECT_METRICS.md").read_text(encoding="utf-8")
    assert main(["run", "cfd", "--case", "fluent-laminar-channel", "--dry-run"]) == 0
    code = "import sys,agentic_simulation_lab;assert not any(x.startswith('ansys.') for x in sys.modules)"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        check=True,
        timeout=60,
    )


if __name__ == "__main__":
    run()
    print("static self-test: PASS")
