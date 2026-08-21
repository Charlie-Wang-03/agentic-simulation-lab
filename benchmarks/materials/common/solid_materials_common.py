"""Shared utilities for the Ansys 2026 R1 material/solid-mechanics suite."""

from __future__ import annotations

import csv
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dynamics_smoke_common import LOGS, ROOT, apdl_path, run_mapdl, svg_plot


MATERIALS_OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "materials"
MATERIALS_LOGS = LOGS / "materials"


def ensure_dirs() -> None:
    MATERIALS_OUT.mkdir(parents=True, exist_ok=True)
    MATERIALS_LOGS.mkdir(parents=True, exist_ok=True)


def case_paths(case: str) -> dict[str, Path]:
    ensure_dirs()
    run_dir = MATERIALS_OUT / case
    run_dir.mkdir(parents=True, exist_ok=True)
    return {
        "dir": run_dir,
        "input": run_dir / f"{case}.inp",
        "solver": run_dir / f"{case}_solver.out",
        "result": run_dir / f"{case}_results.json",
        "curve": run_dir / f"{case}_curve.csv",
        "plot": run_dir / f"{case}.svg",
        "log": MATERIALS_LOGS / f"{case}.log",
    }


def clean_case(case: str) -> dict[str, Path]:
    paths = case_paths(case)
    for path in paths["dir"].iterdir():
        if path.is_file():
            path.unlink()
    paths["log"].unlink(missing_ok=True)
    return paths


def run_apdl(case: str, apdl: str, timeout: int = 300) -> dict[str, Path]:
    paths = case_paths(case)
    paths["input"].write_text(apdl, encoding="ascii")
    code = run_mapdl(case, paths["input"], paths["solver"], timeout=timeout)
    if paths["solver"].exists():
        shutil.copy2(paths["solver"], paths["log"])
    if code:
        raise RuntimeError(f"MAPDL failed for {case} (exit {code}); see {paths['solver']}")
    listing = paths["solver"].read_text(encoding="utf-8", errors="replace")
    fatal = [line.strip() for line in listing.splitlines() if "*** ERROR ***" in line]
    if fatal:
        raise RuntimeError(f"MAPDL reported errors for {case}: {fatal[:3]}")
    return paths


def numeric_rows(path: Path, columns: list[str]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for raw in csv.reader(stream):
            if len(raw) < len(columns):
                continue
            try:
                values = [float(raw[i].strip()) for i in range(len(columns))]
            except ValueError:
                continue
            if all(math.isfinite(value) for value in values):
                rows.append(dict(zip(columns, values)))
    if not rows:
        raise RuntimeError(f"No finite numeric rows in {path}")
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Cannot write an empty curve")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rel_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1e-30)


def payload(
    case: str,
    title: str,
    material_model: str,
    analysis: str,
    mesh: dict,
    parameters: dict,
    results: dict,
    theory: dict,
    errors: dict,
    checks: dict[str, bool],
    files: Iterable[Path],
    limitations: list[str] | None = None,
) -> dict:
    return {
        "case": case,
        "title": title,
        "status": "PASS" if checks and all(checks.values()) else "FAIL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver": {"product": "Ansys MAPDL Student", "version": "2026 R1 / 261", "units": "SI"},
        "material_model": material_model,
        "analysis_type": analysis,
        "mesh": mesh,
        "parameters": parameters,
        "results": results,
        "theory": theory,
        "errors": errors,
        "checks": checks,
        "limitations": limitations or [],
        "files": [str(path.resolve()) for path in files if path.exists()],
    }


def finish(case: str, data: dict, curves: list[dict], series, labels) -> int:
    paths = case_paths(case)
    write_csv(paths["curve"], curves)
    svg_plot(paths["plot"], series, data["title"], labels[0], labels[1])
    data["files"] = sorted(set(data["files"] + [str(paths["curve"].resolve()), str(paths["plot"].resolve())]))
    write_json(paths["result"], data)
    print(f"Case {case} {data['status']}")
    return 0 if data["status"] == "PASS" else 1


def ap(path: Path) -> str:
    return apdl_path(path.with_suffix(""))


def solver_count(listing: str, label: str) -> int:
    import re

    match = re.search(rf"NUMBER OF {label}\s*=\s*(\d+)", listing, re.IGNORECASE)
    return int(match.group(1)) if match else 0


__all__ = [
    "MATERIALS_LOGS", "MATERIALS_OUT", "ap", "case_paths", "clean_case", "ensure_dirs",
    "finish", "numeric_rows", "payload", "rel_error", "run_apdl", "write_csv", "write_json",
]
