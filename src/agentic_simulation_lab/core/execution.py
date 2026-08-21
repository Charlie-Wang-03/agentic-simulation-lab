from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from .paths import artifacts_root, project_root
from .registry import Case
from .result_contract import ResultContractError, load_result


def _classify(return_code: int, physics_status: str | None, result_error: str | None = None) -> str:
    if return_code != 0 or result_error or physics_status is None:
        return "FAIL"
    return physics_status


def _timeout_output(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def execute(case: Case, dry_run: bool = False, timeout_seconds: int | None = None) -> dict[str, object]:
    root = project_root()
    script = root / case.entrypoint
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_base = artifacts_root(root)
    run_dir = artifact_base / "runs" / case.domain / case.slug / stamp
    output_dir = (
        artifact_base / "datasets" / case.domain / case.slug / stamp
        if case.role == "dataset"
        else run_dir / "outputs"
    )
    log_dir = artifact_base / "logs" / case.domain / case.slug / stamp
    command = [sys.executable, str(script)]
    effective_timeout = timeout_seconds if timeout_seconds is not None else case.timeout_seconds
    if effective_timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    result_path = output_dir / case.result_file
    record: dict[str, object] = {
        "domain": case.domain, "case": case.slug, "entrypoint": case.entrypoint,
        "command": command, "dry_run": dry_run, "status": "NOT_RUN",
        "run_directory": run_dir.relative_to(root).as_posix(),
        "output_directory": output_dir.relative_to(root).as_posix(),
        "log_directory": log_dir.relative_to(root).as_posix(),
        "authoritative_result": result_path.relative_to(root).as_posix(),
        "result_format": case.result_format,
        "timeout_seconds": effective_timeout,
    }
    if dry_run:
        return record
    run_dir.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=False)
    log_dir.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    common_dirs = [str(p) for p in sorted((root / "benchmarks").glob("*/common"))]
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), *common_dirs, env.get("PYTHONPATH", "")])
    env["AGENTIC_SIMULATION_LAB_ROOT"] = str(root)
    env["AGENTIC_SIM_OUTPUT_DIR"] = str(output_dir)
    env["AGENTIC_SIM_LOG_DIR"] = str(log_dir)
    env["AGENTIC_SIM_RESULT_FILE"] = str(result_path)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=effective_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        (log_dir / "stdout.log").write_text(_timeout_output(exc.stdout), encoding="utf-8")
        (log_dir / "stderr.log").write_text(_timeout_output(exc.stderr), encoding="utf-8")
        record.update({
            "return_code": None,
            "status": "FAIL",
            "process_status": "TIMEOUT",
            "physics_status": None,
            "error": f"case exceeded {effective_timeout} second execution timeout",
        })
        (run_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return record
    (log_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (log_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    result_error = None
    result = None
    try:
        result = load_result(result_path, legacy=case.result_format == "legacy")
    except ResultContractError as exc:
        result_error = str(exc)
    physics_status = result["status"] if result else None
    record.update({
        "return_code": completed.returncode,
        "process_status": "PASS" if completed.returncode == 0 else "FAIL",
        "physics_status": physics_status,
        "status": _classify(completed.returncode, physics_status, result_error),
        "result_error": result_error,
        "result": result,
    })
    (run_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record
