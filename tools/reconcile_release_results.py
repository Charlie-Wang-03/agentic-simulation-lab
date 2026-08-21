"""Reconcile final solver runs into sanitized, public release evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPRESENTATIVE = {
    "mechanical_mapdl": ("mechanics", "static-cantilever"),
    "fluent": ("cfd", "fluent-laminar-channel"),
    "aedt": ("electromagnetics", "electrostatic"),
    "rocky": ("dem", "particle-freefall"),
    "system_coupling": ("multiphysics", "system-coupling-connect"),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def latest_run(domain: str, case: str) -> tuple[Path, dict[str, Any]]:
    records = sorted((ROOT / "artifacts" / "runs" / domain / case).glob("*/run.json"))
    if not records:
        raise RuntimeError(f"no run record for {domain}/{case}")
    return records[-1], read_json(records[-1])


def public_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items() if key not in {"traceback", "command"}}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        root_text = str(ROOT.resolve())
        return value.replace(root_text + "\\", "").replace(root_text + "/", "")
    return value


def result_from_run(run_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    output_dir = ROOT / str(record["output_directory"])
    candidates = [
        output_dir / str(item["path"])
        for item in record.get("observed_result_statuses", [])
        if (output_dir / str(item["path"])).is_file()
    ]
    if not candidates:
        raise RuntimeError(f"run has no result JSON: {public_path(run_path)}")
    return sanitize(read_json(candidates[0]))


def reconcile_case_j() -> None:
    run_path, run = latest_run("phase_reactive", "reactive-cht")
    result = result_from_run(run_path, run)
    diagnostics_path = ROOT / "benchmarks" / "phase_reactive" / "references" / "targeted_diagnostics.json"
    diagnostics = read_json(diagnostics_path)
    diagnostics["case_j"] = {
        "historical_status": "FAIL",
        "corrected_status": result["status"],
        "diagnostic_executed": True,
        "targeted_fix": "Use Fluent's accepted enthalpy field for final-step transient storage measurement.",
        "prepared_method": (
            "Compare inlet/outlet total-enthalpy flux with integrated outer-wall heat and measured "
            "final-step transient enthalpy accumulation; also check mass-flow and carbon-flux closure."
        ),
        "results": result.get("results", {}),
        "checks": result.get("checks", {}),
        "failed_checks": [key for key, passed in result.get("checks", {}).items() if not passed],
        "acceptance_thresholds_changed": False,
        "authoritative_run_record": public_path(run_path),
        "preserved_initial_api_failure": (
            "artifacts/runs/phase_reactive/reactive-cht/20260820T153221Z/run.json"
        ),
    }
    write_json(diagnostics_path, diagnostics)

    suite_path = ROOT / "benchmarks" / "phase_reactive" / "references" / "suite_summary.json"
    suite = read_json(suite_path)
    for item in suite["records"]:
        if item.get("label") == "J":
            item.update(
                {
                    "action": "release_retest",
                    "exit_code": run.get("return_code"),
                    "result": result,
                    "log": public_path(ROOT / str(run["log_directory"]) / "stdout.log"),
                }
            )
            break
    else:
        raise RuntimeError("phase-reactive suite summary has no Case J record")
    suite["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    suite["statuses"]["J"] = result["status"]
    write_json(suite_path, suite)


def reconcile_regressions() -> None:
    cases: dict[str, Any] = {}
    for label, (domain, case) in REPRESENTATIVE.items():
        run_path, run = latest_run(domain, case)
        cases[label] = {
            "domain": domain,
            "case": case,
            "status": run["status"],
            "run_record": public_path(run_path),
            "observed_result_statuses": run.get("observed_result_statuses", []),
        }
    cases["aedt"]["classification"] = (
        "Official AEDT Student discovery passed, but the supported PyAEDT gRPC session failed to start; "
        "no transport bypass was attempted."
    )
    write_json(
        ROOT / "docs" / "release" / "SOLVER_REGRESSION_RESULTS.json",
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_of_truth": "latest durable CLI run records",
            "cases": cases,
        },
    )

    aedt_run_path, aedt_run = latest_run("electromagnetics", "electrostatic")
    aedt_result = result_from_run(aedt_run_path, aedt_run)
    runtime = aedt_result.get("runtime", {})
    discovery = runtime.get("discovery", {})
    write_json(
        ROOT / "benchmarks" / "electromagnetics" / "references" / "release_regression.json",
        {
            "case": "electrostatic",
            "status": aedt_run["status"],
            "product": discovery.get("version_info", {}).get("FileDescription", "AEDT Student"),
            "discovery_trust": discovery.get("trust", {}).get("status", "FAIL"),
            "failure_stage": "supported PyAEDT gRPC session startup",
            "error": aedt_result.get("error"),
            "cleanup_complete": not aedt_result.get("processes_after_close", ["unknown"]),
            "acceptance_thresholds_changed": False,
            "authoritative_run_record": public_path(aedt_run_path),
        },
    )

    manifest_path = ROOT / "benchmarks" / "electromagnetics" / "manifest.json"
    manifest = read_json(manifest_path)
    for case in manifest["cases"]:
        if case["slug"] == "electrostatic":
            case["status"] = "FAIL"
            evidence = "benchmarks/electromagnetics/references/release_regression.json"
            case["evidence"] = evidence
            case["reference"] = evidence
            break
    else:
        raise RuntimeError("electromagnetics manifest has no electrostatic case")
    write_json(manifest_path, manifest)


def main() -> int:
    reconcile_case_j()
    reconcile_regressions()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
