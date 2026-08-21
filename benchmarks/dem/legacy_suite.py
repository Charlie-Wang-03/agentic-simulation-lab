"""Unified runner and existing-output validator for Rocky DEM Cases A-K."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from rocky_smoke_common import OUTPUT_ROOT, run_rocky_script


ROOT = Path(__file__).resolve().parent
SUMMARY = OUTPUT_ROOT / "suite_summary.json"
CASES = [
    ("A", "smoke_particle_freefall.py", OUTPUT_ROOT / "case_a_freefall" / "result.json", 180),
    ("B", "smoke_particle_collision.py", OUTPUT_ROOT / "case_b_collision" / "result.json", 180),
    ("C", "smoke_particle_friction.py", OUTPUT_ROOT / "case_c_friction" / "result.json", 300),
    ("D", "smoke_angle_of_repose.py", OUTPUT_ROOT / "case_d_angle_of_repose" / "result.json", 480),
    ("E", "smoke_hopper_discharge.py", OUTPUT_ROOT / "case_e_hopper" / "result.json", 420),
    ("F", "smoke_rotating_drum.py", OUTPUT_ROOT / "case_f_rotating_drum" / "result.json", 480),
    ("G", "smoke_nonspherical_particles.py", OUTPUT_ROOT / "case_g_nonspherical" / "result.json", 300),
    ("H", "smoke_particle_thermal.py", OUTPUT_ROOT / "case_h_thermal" / "result.json", 240),
    ("I", "smoke_cfd_dem_one_way.py", OUTPUT_ROOT / "case_i_one_way" / "result.json", 300),
    ("J", "smoke_cfd_dem_two_way.py", OUTPUT_ROOT / "case_j_two_way" / "result.json", 240),
    ("K", "smoke_rocky_dataset.py", OUTPUT_ROOT / "dataset" / "dataset_index.json", 600),
]


def run_host(script: str, timeout: int) -> dict:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-u", str(ROOT / script)], cwd=ROOT,
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    return {
        "script": script,
        "return_code": completed.returncode,
        "elapsed_s": time.perf_counter() - started,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def load_result(case: str, path: Path) -> dict:
    if not path.is_file():
        return {"case": case, "status": "MISSING", "result_file": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"case": case, "status": data.get("status", "UNKNOWN"), "result_file": str(path)}
    except Exception as exc:
        return {"case": case, "status": "INVALID JSON", "result_file": str(path), "error": repr(exc)}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="rerun every solver case")
    mode.add_argument("--validate-existing", action="store_true", help="validate current outputs (default)")
    args = parser.parse_args()
    launch_records = []
    if args.run:
        # Prerequisites for official CFD coupling.
        launch_records.append(run_host("logs/rocky_dem/probe_f2r_export.py", 300))
        launch_records.append(run_host("logs/rocky_dem/prepare_two_way_fluent.py", 180))
        for case, script, _, timeout in CASES:
            launch_records.append(run_rocky_script(script, case_name=f"suite_case_{case.lower()}", timeout_s=timeout))

    validation = [load_result(case, path) for case, _, path, _ in CASES]
    dataset_validation = run_host("validate_rocky_dataset.py", 60)
    unexpected = [x for x in validation if x["status"] not in {"PASS", "BLOCKED BY CURRENT API", "BLOCKED BY STUDENT LIMIT"}]
    blocked = [x for x in validation if x["status"].startswith("BLOCKED BY")]
    status = "FAIL" if unexpected or dataset_validation["return_code"] else ("PASS WITH EXPLICIT BLOCK" if blocked else "PASS")
    payload = {
        "status": status,
        "mode": "run" if args.run else "validate-existing",
        "cases": validation,
        "blocked_cases": blocked,
        "unexpected_failures": unexpected,
        "dataset_validator": dataset_validation,
        "launch_records": launch_records,
        "pass_count": sum(x["status"] == "PASS" for x in validation),
        "case_count": len(validation),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
