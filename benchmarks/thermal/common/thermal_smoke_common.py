"""Shared infrastructure for the Ansys MAPDL thermal smoke benchmarks."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from dynamics_smoke_common import LOGS, OUT, apdl_path, run_mapdl, svg_plot, write_csv, write_json


ROOT = Path(__file__).resolve().parent


def clean_case(case: str) -> None:
    OUT.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    for path in OUT.glob(case + "*"):
        if path.is_file():
            path.unlink()


def run_apdl(case: str, text: str, timeout: int = 180) -> tuple[Path, Path]:
    inp = OUT / f"{case}.inp"
    solver_out = OUT / f"{case}_solver.out"
    inp.write_text(text, encoding="ascii")
    code = run_mapdl(case, inp, solver_out, timeout=timeout)
    if code != 0:
        raise RuntimeError(f"MAPDL failed for {case} with exit code {code}; see {solver_out}")
    return inp, solver_out


def numeric_rows(path: Path, names: list[str]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for raw in csv.reader(stream):
            if len(raw) < len(names):
                continue
            try:
                values = [float(raw[i].strip()) for i in range(len(names))]
            except ValueError:
                continue
            if all(math.isfinite(v) for v in values):
                rows.append(dict(zip(names, values)))
    if not rows:
        raise RuntimeError(f"No numeric data found in {path}")
    return rows


def scalar_row(path: Path, names: list[str]) -> dict[str, float]:
    return numeric_rows(path, names)[0]


def average_by_x(rows: list[dict[str, float]]) -> list[dict[str, float]]:
    buckets: dict[float, list[float]] = {}
    for row in rows:
        x = round(row["x_m"], 12)
        buckets.setdefault(x, []).append(row["temperature_c"])
    return [
        {"x_m": x, "temperature_c": sum(values) / len(values)}
        for x, values in sorted(buckets.items())
    ]


def rel_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1.0e-30)


def result_payload(case: str, analysis: str, model: dict, mesh: dict, results: dict,
                   theory: dict, errors: dict, checks: dict, files: list[Path]) -> dict:
    return {
        "case": case,
        "analysis_type": analysis,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver": {"product": "Ansys MAPDL", "version": "2026 R1 / 261"},
        "model": model,
        "mesh": mesh,
        "results": results,
        "theory": theory,
        "errors": errors,
        "checks": checks,
        "files": [str(p.resolve()) for p in files],
    }


def apdl_export_nodes(raw_path: Path) -> str:
    return f"""ALLSEL,ALL
*GET,NN,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_path(raw_path.with_suffix(''))}','csv'
*DO,II,1,NN
  *GET,NX,NODE,NID,LOC,X
  *GET,NT,NODE,NID,TEMP
  *VWRITE,NID,NX,NT
  (F12.0,',',E22.14,',',E22.14)
  NID=NDNEXT(NID)
*ENDDO
*CFCLOS"""


def apdl_sum_reaction(x: float, variable: str = "QREACTION") -> str:
    return f"""NSEL,S,LOC,X,{x:.16g}
*GET,NRC,NODE,0,COUNT
*GET,NRN,NODE,0,NUM,MIN
{variable}=0
*DO,II,1,NRC
  *GET,NQR,NODE,NRN,RF,HEAT
  {variable}={variable}+NQR
  NRN=NDNEXT(NRN)
*ENDDO
ALLSEL,ALL"""
