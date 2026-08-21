"""Shared launcher and result helpers for the Rocky DEM smoke suite.

Rocky 2026 R1 Student starts and solves reliably through its built-in
PrePost scripting entry point.  The PyRocky RPC route is probed separately;
it is not silently substituted with a home-grown DEM implementation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem"
LOG_ROOT = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs")) / "rocky_dem"
DEFAULT_ROCKY_EXE = Path(
    r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\rocky\bin\Rocky.exe"
)
DEFAULT_ROCKY_SOLVER_EXE = DEFAULT_ROCKY_EXE.with_name("RockySolver.exe")


def ensure_directories() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)


def rocky_executable() -> Path:
    configured = os.environ.get("ROCKY_EXE")
    executable = Path(configured) if configured else DEFAULT_ROCKY_EXE
    if not executable.is_file():
        raise FileNotFoundError(f"Rocky executable not found: {executable}")
    return executable


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_rocky_script(
    script: str | Path,
    *,
    case_name: str,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    """Run a real Rocky built-in PrePost script in headless mode."""
    ensure_directories()
    script_path = Path(script).resolve()
    if not script_path.is_file():
        raise FileNotFoundError(script_path)
    executable = rocky_executable()
    stdout_path = LOG_ROOT / f"{case_name}_stdout.log"
    stderr_path = LOG_ROOT / f"{case_name}_stderr.log"
    server_error_path = LOG_ROOT / f"{case_name}_rocky_error.log"
    command = [
        str(executable),
        "--headless",
        "--redirect-error",
        str(server_error_path),
        "--script",
        str(script_path),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    started = time.perf_counter()
    timed_out = False
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        process = subprocess.Popen(
            command,
            cwd=executable.parent,
            stdout=stdout,
            stderr=stderr,
            creationflags=creationflags,
        )
        try:
            return_code = process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            return_code = process.wait(timeout=30)
    result = {
        "case": case_name,
        "command": command,
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_s": time.perf_counter() - started,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "rocky_error_log": str(server_error_path),
    }
    write_json(LOG_ROOT / f"{case_name}_launcher.json", result)
    return result


def result_status(result_path: str | Path) -> str:
    path = Path(result_path)
    if not path.is_file():
        return "FAIL"
    return str(read_json(path).get("status", "FAIL"))
