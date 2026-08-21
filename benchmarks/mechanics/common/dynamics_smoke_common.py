"""Shared helpers for the independent Mechanical/MAPDL dynamics smoke tests."""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs"))
LOGS = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs"))
AWP_ROOT261 = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"
MAPDL_EXE = AWP_ROOT261 + r"\ansys\bin\winx64\ANSYS261.exe"
MECH_EXE = AWP_ROOT261 + r"\aisol\bin\winx64\AnsysWBU.exe"


def apdl_path(path: Path) -> str:
    return path.resolve().as_posix()


def run_mapdl(job: str, input_file: Path, solver_output: Path, timeout: int = 180) -> int:
    OUT.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({"AWP_ROOT261": AWP_ROOT261, "ANSYS261_DIR": AWP_ROOT261 + r"\ansys"})
    cmd = [MAPDL_EXE, "-b", "-np", "2", "-j", job, "-dir", str(OUT), "-i", str(input_file), "-o", str(solver_output)]
    print("MAPDL:", subprocess.list2cmdline(cmd), flush=True)
    done = subprocess.run(cmd, cwd=OUT, env=env, timeout=timeout, check=False)
    print("MAPDL exit code:", done.returncode, flush=True)
    return int(done.returncode)


def read_numeric_csv(path: Path, columns: list[str]) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(encoding="utf-8-sig") as file:
        for raw in csv.reader(file):
            if not raw or len(raw) < len(columns):
                continue
            try:
                values = [float(raw[i].strip()) for i in range(len(columns))]
            except ValueError:
                continue
            if all(math.isfinite(value) for value in values):
                rows.append(dict(zip(columns, values)))
    return rows


def write_csv(path: Path, rows: list[dict[str, float]]) -> None:
    if not rows:
        raise RuntimeError("Cannot write an empty history")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def svg_plot(path: Path, series: list[tuple[list[float], list[float], str]], title: str, xlabel: str, ylabel: str) -> None:
    width, height, margin = 760, 460, 58
    xs = [x for sx, _, _ in series for x in sx]
    ys = [y for _, sy, _ in series for y in sy]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if xmax == xmin:
        xmax += 1.0
    if ymax == ymin:
        ymax += 1.0
    px = lambda x: margin + (x-xmin)/(xmax-xmin)*(width-2*margin)
    py = lambda y: height-margin-(y-ymin)/(ymax-ymin)*(height-2*margin)
    colors = ["#2563eb", "#dc2626", "#059669", "#9333ea"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>', f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>', f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black"/>']
    for index, (sx, sy, label) in enumerate(series):
        points = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in zip(sx, sy))
        color = colors[index % len(colors)]
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{width-margin-170}" y="{margin+18*index}" font-family="sans-serif" font-size="12" fill="{color}">{label}</text>')
    parts += [f'<text x="{width/2}" y="{height-10}" text-anchor="middle" font-family="sans-serif">{xlabel}</text>', f'<text transform="translate(16,{height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif">{ylabel}</text>', '</svg>']
    path.write_text("\n".join(parts), encoding="utf-8")
