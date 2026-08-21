"""Shared MAPDL 261 helpers for the acoustic smoke-test suite."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent
ACOUSTICS_OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "acoustics"
ACOUSTICS_LOGS = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs")) / "acoustics"
AWP_ROOT261 = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"
MAPDL_EXE = Path(AWP_ROOT261) / "ansys" / "bin" / "winx64" / "ANSYS261.exe"
AIR_DENSITY = 1.2041
SOUND_SPEED = 343.24
REFERENCE_PRESSURE_PA = 20.0e-6


def ensure_dirs(*parts: str) -> tuple[Path, Path]:
    out = ACOUSTICS_OUT.joinpath(*parts)
    logs = ACOUSTICS_LOGS.joinpath(*parts)
    out.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    return out, logs


def apdl_stem(path: Path) -> str:
    """Return an absolute POSIX-style APDL path without its suffix."""
    return path.resolve().with_suffix("").as_posix()


def run_apdl(case_name: str, text: str, timeout: int = 300) -> dict:
    out, logs = ensure_dirs(case_name)
    inp = out / f"{case_name}.inp"
    solver_out = out / f"{case_name}.out"
    inp.write_text(text, encoding="ascii")
    env = os.environ.copy()
    env.update({"AWP_ROOT261": AWP_ROOT261, "ANSYS261_DIR": str(Path(AWP_ROOT261) / "ansys")})
    command = [
        str(MAPDL_EXE), "-b", "-np", "2", "-j", case_name,
        "-dir", str(out), "-i", str(inp), "-o", str(solver_out),
    ]
    print("MAPDL:", subprocess.list2cmdline(command), flush=True)
    started = datetime.now(timezone.utc)
    completed = subprocess.run(command, cwd=out, env=env, timeout=timeout, check=False)
    log_copy = logs / solver_out.name
    if solver_out.is_file():
        shutil.copy2(solver_out, log_copy)
    evidence = {
        "case_name": case_name,
        "command": command,
        "exit_code": int(completed.returncode),
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(inp.resolve()),
        "solver_output": str(solver_out.resolve()),
        "log_copy": str(log_copy.resolve()),
    }
    print(json.dumps(evidence, indent=2), flush=True)
    if completed.returncode != 0:
        raise RuntimeError(f"MAPDL failed for {case_name}; see {solver_out}")
    return evidence


def read_numeric_rows(path: Path, columns: list[str]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(encoding="utf-8-sig", errors="ignore", newline="") as stream:
        for raw in csv.reader(stream):
            if len(raw) < len(columns):
                continue
            try:
                vals = [float(raw[i].strip()) for i in range(len(columns))]
            except ValueError:
                continue
            if all(math.isfinite(x) for x in vals):
                rows.append(dict(zip(columns, vals)))
    return rows


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def complex_metrics(real: float, imag: float) -> tuple[float, float]:
    value = complex(real, imag)
    return abs(value), math.degrees(math.atan2(value.imag, value.real))


def spl_db(amplitude_pa: float) -> float:
    return 20.0 * math.log10(max(abs(amplitude_pa), 1.0e-30) / REFERENCE_PRESSURE_PA)


def dominant_peak(x: Iterable[float], y: Iterable[float], edge: int = 1) -> tuple[float, float, int]:
    xa = np.asarray(list(x), dtype=float)
    ya = np.asarray(list(y), dtype=float)
    if xa.size <= 2 * edge:
        raise ValueError("Not enough samples for peak detection")
    interior = ya[edge: ya.size - edge]
    idx = int(np.argmax(interior)) + edge
    return float(xa[idx]), float(ya[idx]), idx


def svg_plot(path: Path, series: list[tuple[list[float], list[float], str]], title: str, xlabel: str, ylabel: str) -> None:
    width, height, margin = 800, 480, 62
    xs = [v for x, _, _ in series for v in x]
    ys = [v for _, y, _ in series for v in y]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if xmax == xmin: xmax += 1.0
    if ymax == ymin: ymax += 1.0
    px = lambda x: margin + (x-xmin)/(xmax-xmin)*(width-2*margin)
    py = lambda y: height-margin-(y-ymin)/(ymax-ymin)*(height-2*margin)
    colors = ["#2563eb", "#dc2626", "#059669", "#9333ea"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>', f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>', f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black"/>']
    for i, (sx, sy, label) in enumerate(series):
        points = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in zip(sx, sy))
        color = colors[i % len(colors)]
        parts += [f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>', f'<text x="{width-margin-190}" y="{margin+18*i}" font-family="sans-serif" font-size="12" fill="{color}">{label}</text>']
    parts += [f'<text x="{width/2}" y="{height-12}" text-anchor="middle" font-family="sans-serif">{xlabel}</text>', f'<text transform="translate(18,{height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif">{ylabel}</text>', "</svg>"]
    path.write_text("\n".join(parts), encoding="utf-8")


def classify_solver_restriction(solver_output: Path) -> str | None:
    if not solver_output.is_file():
        return None
    text = solver_output.read_text(encoding="utf-8", errors="ignore").lower()
    markers = ("license", "not available for this product", "product restriction", "student")
    return "BLOCKED BY STUDENT LIMIT" if any(marker in text for marker in markers) else None
