"""Unified real-solver runner and existing-output validator for SPH Cases A-L."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from free_surface_sph_common import LOG_ROOT, OUTPUT_ROOT, ROCKY_EXE, ROOT

SUMMARY = OUTPUT_ROOT / "suite_summary.json"
ANSYS_PYTHON = Path(sys.executable)
CASES = [
    ("A", "rocky", "smoke_sph_hydrostatic.py", OUTPUT_ROOT / "case_a_hydrostatic" / "result.json", 300),
    ("B", "rocky", "smoke_sph_dam_break.py", OUTPUT_ROOT / "case_b_dam_break" / "result.json", 300),
    ("C", "rocky", "smoke_sph_sloshing.py", OUTPUT_ROOT / "case_c_sloshing" / "result.json", 900),
    ("D", "rocky", "smoke_sph_jet_impact.py", OUTPUT_ROOT / "case_d_jet_impact" / "result.json", 300),
    ("E", "rocky", "smoke_sph_moving_boundary.py", OUTPUT_ROOT / "case_e_moving_boundary" / "result.json", 300),
    ("F", "host", "smoke_sph_non_newtonian.py", OUTPUT_ROOT / "case_f_non_newtonian" / "result.json", 60),
    ("G", "rocky", "smoke_sph_thermal.py", OUTPUT_ROOT / "case_g_thermal" / "result.json", 480),
    ("H", "rocky", "smoke_sph_rigid_body.py", OUTPUT_ROOT / "case_h_rigid_body" / "result.json", 360),
    ("I", "host", "smoke_sph_flexible_structure.py", OUTPUT_ROOT / "case_i_flexible_structure" / "result.json", 60),
    ("J", "rocky", "smoke_sph_resolution.py", OUTPUT_ROOT / "case_j_resolution" / "result.json", 600),
    ("K", "host", "smoke_sph_vof_comparison.py", OUTPUT_ROOT / "case_k_vof_comparison" / "result.json", 60),
    ("L", "rocky", "smoke_sph_dataset.py", OUTPUT_ROOT / "case_l_dataset" / "result.json", 1200),
]


def run_host(script: str, timeout_s: int, python_executable: Path | None = None) -> dict:
    started = time.perf_counter()
    python_command = str(python_executable if python_executable and python_executable.is_file() else sys.executable)
    completed = subprocess.run([python_command, "-u", str(ROOT / script)], cwd=ROOT, capture_output=True, text=True, timeout=timeout_s, check=False)
    return {"script": script, "return_code": completed.returncode, "elapsed_s": time.perf_counter()-started, "stdout_tail": completed.stdout[-3000:], "stderr_tail": completed.stderr[-3000:]}


def run_rocky(case: str, script: str, result_path: Path, timeout_s: int) -> dict:
    """Launch GUI-subsystem Rocky and wait for a newer result artifact."""
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    before = result_path.stat().st_mtime_ns if result_path.is_file() else -1
    error_log = LOG_ROOT / f"suite_case_{case.lower()}_rocky_error.log"
    command = [str(ROCKY_EXE), "--headless", "--redirect-error", str(error_log), "--script", str(ROOT / script)]
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROCKY_EXE.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        launcher_return_code = process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        launcher_return_code = process.wait(timeout=10)
        return {
            "case": case,
            "script": script,
            "launcher_return_code": launcher_return_code,
            "result_updated": False,
            "timed_out": True,
            "elapsed_s": time.perf_counter() - started,
            "rocky_error_log": str(error_log),
        }
    deadline = time.monotonic() + timeout_s
    updated = False
    while time.monotonic() < deadline:
        if result_path.is_file() and result_path.stat().st_mtime_ns > before:
            try:
                json.loads(result_path.read_text(encoding="utf-8"))
                updated = True
                break
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(2.0)
    return {"case": case, "script": script, "launcher_return_code": launcher_return_code, "result_updated": updated, "timed_out": not updated, "elapsed_s": time.perf_counter()-started, "rocky_error_log": str(error_log)}


def load_case(case: str, path: Path) -> dict:
    if not path.is_file():
        return {"case": case, "status": "MISSING", "result_file": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"case": case, "status": data.get("status", "UNKNOWN"), "result_file": str(path), "checks": data.get("checks", {})}
    except Exception as exc:
        return {"case": case, "status": "INVALID JSON", "result_file": str(path), "error": repr(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="run all real solver and host-side cases")
    mode.add_argument("--validate-existing", action="store_true", help="validate current outputs (default)")
    args = parser.parse_args()
    launches = []
    if args.run:
        for case, kind, script, result_path, timeout_s in CASES:
            launches.append(run_rocky(case, script, result_path, timeout_s) if kind == "rocky" else run_host(script, timeout_s))
        launches.append(run_host("prepare_sph_dataset.py", 120, ANSYS_PYTHON))
    cases = [load_case(case, path) for case, _, _, path, _ in CASES]
    dataset_validation = run_host("validate_sph_dataset.py", 120, ANSYS_PYTHON)
    blocked = [case for case in cases if str(case["status"]).startswith("BLOCKED BY")]
    failures = [case for case in cases if case["status"] != "PASS" and not str(case["status"]).startswith("BLOCKED BY")]
    status = "FAIL" if failures or dataset_validation["return_code"] else ("PASS WITH EXPLICIT BLOCK" if blocked else "PASS")
    payload = {"status": status, "mode": "run" if args.run else "validate-existing", "product": "Ansys Rocky Student 26.1 native SPH", "cases": cases, "blocked_cases": blocked, "unexpected_failures": failures, "dataset_validator": dataset_validation, "launch_records": launches, "pass_count": sum(case["status"] == "PASS" for case in cases), "case_count": len(cases)}
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
