"""Shared infrastructure for Ansys Fluent 2026 R1 CFD smoke tests."""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import ansys.fluent.core as pyfluent


ROOT = Path(__file__).resolve().parent
OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs"))
LOGS = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs"))
AWP_ROOT261 = Path(r"C:\Program Files\ANSYS Inc\ANSYS Student\v261")
FLUENT_EXE = AWP_ROOT261 / "fluent" / "ntbin" / "win64" / "fluent.exe"


def ensure_dirs() -> None:
    OUT.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)


def clean_case(case: str) -> None:
    ensure_dirs()
    for folder in (OUT, LOGS):
        for path in folder.glob(f"{case}*"):
            if path.is_file():
                path.unlink()


def fluent_processes() -> list[dict[str, str | int]]:
    """Return a conservative snapshot of Fluent-related processes."""
    completed = subprocess.run(
        ["tasklist", "/fo", "csv", "/nh"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    names = {"fluent.exe", "fluent_aeneid.exe", "cortex.exe", "cx.exe"}
    rows: list[dict[str, str | int]] = []
    for row in csv.reader(completed.stdout.splitlines()):
        if len(row) >= 2 and row[0].lower() in names:
            try:
                pid = int(row[1])
            except ValueError:
                pid = -1
            rows.append({"name": row[0], "pid": pid})
    return rows


def launch_fluent(
    *,
    dimension: int = 2,
    processor_count: int = 2,
    cwd: Path | None = None,
    start_transcript: bool = True,
):
    """Launch the locally installed Student Fluent 261 solver via PyFluent."""
    if not FLUENT_EXE.is_file():
        raise FileNotFoundError(f"Fluent executable not found: {FLUENT_EXE}")
    run_dir = (cwd or OUT).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    child_env = dict(os.environ)
    child_env["AWP_ROOT261"] = str(AWP_ROOT261)
    fluent_temp = OUT / "runtime_cache" / "fluent-temp"
    fluent_temp.mkdir(parents=True, exist_ok=True)
    child_env["TEMP"] = child_env["TMP"] = str(fluent_temp)
    # PyFluent creates the server-info handshake file in the client process
    # before applying its child ``env`` mapping. Redirect tempfile for that
    # short launch window as well, then restore the parent state.
    old_tempdir = tempfile.tempdir
    tempfile.tempdir = str(fluent_temp)
    try:
        return pyfluent.launch_fluent(
            product_version="261",
            mode="solver",
            dimension=dimension,
            precision="double",
            processor_count=processor_count,
            ui_mode="no_gui",
            cleanup_on_exit=True,
            start_transcript=start_transcript,
            start_timeout=120,
            cwd=run_dir,
            fluent_path=FLUENT_EXE,
            env=child_env,
        )
    finally:
        tempfile.tempdir = old_tempdir


@contextmanager
def fluent_session(**kwargs: Any) -> Iterator[Any]:
    """Launch Fluent and guarantee a graceful exit on every code path."""
    session = launch_fluent(**kwargs)
    try:
        yield session
    finally:
        try:
            session.exit()
        except Exception:
            # cleanup_on_exit remains the final safety net.
            pass


def tui(session: Any, command: str) -> Any:
    """Execute one Fluent TUI command through the supported Scheme bridge."""
    escaped = command.replace("\\", "\\\\").replace('"', '\\"')
    return session.scheme_eval.string_eval(f'(ti-menu-load-string "{escaped}")')


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def read_fluent_ascii_export(path: Path) -> list[dict[str, float]]:
    """Parse Fluent's comma-delimited ASCII surface export."""
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    header_index = next(
        (i for i, line in enumerate(lines) if "," in line and any(k in line.lower() for k in ("coordinate", "pressure", "velocity", "mach", "temperature", "density"))),
        None,
    )
    if header_index is None:
        raise RuntimeError(f"No Fluent ASCII header found in {path}")
    reader = csv.DictReader(lines[header_index:])
    rows: list[dict[str, float]] = []
    for raw in reader:
        parsed: dict[str, float] = {}
        try:
            for key, value in raw.items():
                if key is None or value is None:
                    continue
                clean_key = key.strip().strip('"').lower().replace(" ", "-")
                parsed[clean_key] = float(value.strip().strip('"'))
        except ValueError:
            continue
        if parsed:
            rows.append(parsed)
    if not rows:
        raise RuntimeError(f"No numeric Fluent data found in {path}")
    return rows


def rel_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1.0e-30)


def base_payload(case: str, analysis_type: str) -> dict[str, Any]:
    return {
        "case": case,
        "analysis_type": analysis_type,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "automation": {
            "pyfluent_version": pyfluent.__version__,
            "fluent_executable": str(FLUENT_EXE),
            "awp_root261_scope": "child process only",
        },
        "solver": {"product": "Ansys Fluent Student", "requested_version": "2026 R1 / 261"},
    }


def svg_xy_plot(
    path: Path,
    rows: list[tuple[float, float]],
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    reference: list[tuple[float, float]] | None = None,
) -> Path:
    """Write a dependency-free, meaningful SVG XY plot."""
    all_rows = rows + (reference or [])
    xs = [p[0] for p in all_rows]
    ys = [p[1] for p in all_rows]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if math.isclose(xmin, xmax):
        xmax = xmin + 1.0
    if math.isclose(ymin, ymax):
        ymax = ymin + 1.0
    width, height = 800, 520
    left, right, top, bottom = 85, 25, 55, 70
    pw, ph = width - left - right, height - top - bottom

    def point(p: tuple[float, float]) -> str:
        x = left + (p[0] - xmin) / (xmax - xmin) * pw
        y = top + (ymax - p[1]) / (ymax - ymin) * ph
        return f"{x:.2f},{y:.2f}"

    measured = " ".join(point(p) for p in rows)
    ref = " ".join(point(p) for p in (reference or []))
    ref_svg = f'<polyline points="{ref}" fill="none" stroke="#d55e00" stroke-width="2" stroke-dasharray="7 5"/>' if ref else ""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="20">{title}</text>
<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" stroke="black"/>
<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" stroke="black"/>
<polyline points="{measured}" fill="none" stroke="#0072b2" stroke-width="3"/>
{ref_svg}
<text x="{left+pw/2}" y="{height-20}" text-anchor="middle" font-family="sans-serif">{xlabel}</text>
<text x="20" y="{top+ph/2}" text-anchor="middle" transform="rotate(-90 20 {top+ph/2})" font-family="sans-serif">{ylabel}</text>
<text x="{left}" y="{top+ph+22}" font-family="monospace" font-size="11">{xmin:.4g}</text>
<text x="{left+pw}" y="{top+ph+22}" text-anchor="end" font-family="monospace" font-size="11">{xmax:.4g}</text>
<text x="{left-8}" y="{top+ph}" text-anchor="end" font-family="monospace" font-size="11">{ymin:.4g}</text>
<text x="{left-8}" y="{top+6}" text-anchor="end" font-family="monospace" font-size="11">{ymax:.4g}</text>
</svg>'''
    path.write_text(svg, encoding="utf-8")
    return path


def svg_field_map(
    path: Path,
    rows: list[tuple[float, float, float]],
    *,
    title: str,
    xlabel: str = "x (m)",
    ylabel: str = "y (m)",
    max_points: int = 12000,
) -> Path:
    """Write a compact SVG colored-point map for exported Fluent field data."""
    if len(rows) > max_points:
        stride = math.ceil(len(rows) / max_points)
        rows = rows[::stride]
    xs, ys, vals = zip(*rows)
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    vmin, vmax = min(vals), max(vals)
    width, height = 900, 560
    left, right, top, bottom = 80, 100, 50, 65
    pw, ph = width-left-right, height-top-bottom
    def color(v: float) -> str:
        t = 0.5 if math.isclose(vmin, vmax) else max(0.0, min(1.0, (v-vmin)/(vmax-vmin)))
        r = int(255 * max(0.0, min(1.0, 1.5*t)))
        b = int(255 * max(0.0, min(1.0, 1.5*(1-t))))
        g = int(255 * max(0.0, 1.0-2.0*abs(t-0.5)))
        return f"#{r:02x}{g:02x}{b:02x}"
    circles = []
    for x,y,v in rows:
        px = left + (x-xmin)/max(xmax-xmin,1e-30)*pw
        py = top + (ymax-y)/max(ymax-ymin,1e-30)*ph
        circles.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.2" fill="{color(v)}"/>')
    bars = []
    for i in range(80):
        value = vmin + (vmax-vmin)*i/79
        bars.append(f'<rect x="{width-right+25}" y="{top+ph*(79-i)/80:.2f}" width="18" height="{ph/80+1:.2f}" fill="{color(value)}"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/><text x="{width/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="20">{title}</text>
<rect x="{left}" y="{top}" width="{pw}" height="{ph}" fill="#eeeeee" stroke="black"/>{''.join(circles)}{''.join(bars)}
<text x="{left+pw/2}" y="{height-18}" text-anchor="middle" font-family="sans-serif">{xlabel}</text>
<text x="18" y="{top+ph/2}" text-anchor="middle" transform="rotate(-90 18 {top+ph/2})" font-family="sans-serif">{ylabel}</text>
<text x="{width-right+50}" y="{top+10}" font-family="monospace" font-size="11">{vmax:.4g}</text>
<text x="{width-right+50}" y="{top+ph}" font-family="monospace" font-size="11">{vmin:.4g}</text></svg>'''
    path.write_text(svg, encoding="utf-8")
    return path
