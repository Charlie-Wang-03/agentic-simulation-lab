"""Shared infrastructure for porous-media and geomechanics smoke tests."""

from __future__ import annotations

import json
import math
import shutil
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dynamics_smoke_common import apdl_path, run_mapdl, svg_plot
from fluent_smoke_common import ROOT, fluent_session
from fluent_smoke_common import read_fluent_ascii_export
from fluent_mesh import rectangular_2d


POROUS_OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "porous_geomechanics"
POROUS_LOGS = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs")) / "porous_geomechanics"


def ensure_dirs() -> None:
    POROUS_OUT.mkdir(parents=True, exist_ok=True)
    POROUS_LOGS.mkdir(parents=True, exist_ok=True)


def case_paths(case: str) -> dict[str, Path]:
    ensure_dirs()
    folder = POROUS_OUT / case
    folder.mkdir(parents=True, exist_ok=True)
    return {
        "dir": folder,
        "input": folder / f"{case}.inp",
        "solver": folder / f"{case}_solver.out",
        "result": folder / f"{case}_results.json",
        "log": POROUS_LOGS / f"{case}.log",
    }


def clean_case(case: str) -> dict[str, Path]:
    paths = case_paths(case)
    for path in paths["dir"].iterdir():
        if path.is_file():
            path.unlink()
    paths["log"].unlink(missing_ok=True)
    return paths


def run_apdl(case: str, text: str, timeout: int = 300) -> dict[str, Path]:
    paths = case_paths(case)
    paths["input"].write_text(text, encoding="ascii")
    code = run_mapdl_raw(case, paths["input"], paths["solver"], timeout)
    if paths["solver"].is_file():
        shutil.copy2(paths["solver"], paths["log"])
    listing = paths["solver"].read_text(encoding="utf-8", errors="replace") if paths["solver"].is_file() else ""
    return {**paths, "exit_code": code, "listing": listing}


def run_mapdl_raw(case: str, input_path: Path, output_path: Path, timeout: int) -> int:
    return run_mapdl(case, input_path, output_path, timeout=timeout)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    def _json_default(value: Any) -> Any:
        if hasattr(value, "item"):
            return value.item()
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")
    return path


def status_payload(case: str, title: str, status: str, **items: Any) -> dict[str, Any]:
    return {
        "case": case,
        "title": title,
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver_version": "Ansys Student 2026 R1 / 261",
        "units": "SI",
        **items,
    }


def relative_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1.0e-30)


def finite_tree(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite_tree(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite_tree(v) for v in value)
    return True


def classify_solver_error(exc: Exception) -> tuple[str, str]:
    """Return an honest blocked/fail label without disguising solver errors."""
    message = f"{type(exc).__name__}: {exc}"
    low = message.lower()
    recent_solver_text = ""
    try:
        candidates = sorted(
            [*POROUS_OUT.rglob("fluent-*.trn"), *POROUS_OUT.rglob("*_solver.out")],
            key=lambda p: p.stat().st_mtime, reverse=True,
        )[:4]
        recent_solver_text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")[-12000:] for p in candidates
        ).lower()
    except Exception:
        pass
    true_license_error = any(token in low for token in (
        "cannot initialize ansys licensing", "ansys license manager error",
        "unexpected license problem", "could not connect to any license server",
    ))
    if true_license_error or "cannot initialize ansys licensing" in recent_solver_text:
        return "BLOCKED BY CURRENT LICENSE CONTEXT", message
    if "student" in low and ("limit" in low or "does not support" in low):
        return "BLOCKED BY STUDENT LIMIT", message
    if "not available" in low or "unknown command" in low or "attribute" in low:
        return "BLOCKED BY CURRENT API", message
    return "FAIL", message


def solve_porous_channel(
    case: str,
    velocity: float,
    *,
    viscous_resistance: tuple[float, float] = (1.0e8, 1.0e8),
    inertial_resistance: tuple[float, float] = (0.0, 0.0),
    length: float = 1.0,
    height: float = 0.10,
    rho: float = 1000.0,
    mu: float = 1.0e-3,
    porosity: float = 0.35,
    nx: int = 80,
    ny: int = 8,
    iterations: int = 400,
) -> dict[str, Any]:
    """Solve one uniform Fluent porous block and export nodal fields."""
    paths = case_paths(case)
    tag = f"u{velocity:.8g}".replace(".", "p")
    mesh = paths["dir"] / f"{tag}.msh"
    raw = paths["dir"] / f"{tag}_field.csv"
    cas = paths["dir"] / f"{tag}.cas.h5"
    xs = [length * i / nx for i in range(nx + 1)]
    ys = [height * j / ny for j in range(ny + 1)]
    mesh_stats = rectangular_2d(
        mesh, xs, ys,
        bottom=("bottom-symmetry", "symmetry"),
        top=("top-symmetry", "symmetry"),
    )
    with fluent_session(dimension=2, processor_count=1, cwd=paths["dir"]) as s:
        s.settings.file.read_mesh(file_name=str(mesh))
        s.settings.setup.models.viscous.model = "laminar"
        fluid = s.settings.setup.materials.fluid["air"]
        fluid.density.value = rho
        fluid.viscosity.value = mu
        zone = s.settings.setup.cell_zone_conditions.fluid["fluid"].porous_zone
        zone.porous = True
        zone.porosity.value = porosity
        for index, value in enumerate(viscous_resistance):
            zone.viscous_resistance[index].value = value
        for index, value in enumerate(inertial_resistance):
            zone.inertial_resistance[index].value = value
        inlet = s.settings.setup.boundary_conditions.velocity_inlet["inlet"]
        inlet.momentum.velocity_magnitude.value = velocity
        for name, x in (("station-up", 0.10 * length), ("station-down", 0.90 * length)):
            s.settings.results.surfaces.line_surface[name] = {
                "p0": [x, 0.0, 0.0], "p1": [x, height, 0.0]
            }
        s.settings.solution.initialization.hybrid_initialize()
        s.settings.solution.run_calculation.iterate(iter_count=iterations)
        s.settings.file.export.ascii(
            file_name=str(raw),
            surface_name_list=["interior", "inlet", "outlet", "station-up", "station-down"],
            delimiter="comma",
            quantities=["x-coordinate", "y-coordinate", "pressure", "x-velocity", "y-velocity"],
            location="node",
        )
        s.settings.file.write_case_data(file_name=str(cas))
        zone_state = zone.get_state()
    rows = read_fluent_ascii_export(raw)
    up = [r for r in rows if abs(r["x-coordinate"] - 0.10 * length) < 1.0e-9]
    down = [r for r in rows if abs(r["x-coordinate"] - 0.90 * length) < 1.0e-9]
    if not up or not down:
        raise RuntimeError(f"Missing pressure station data: up={len(up)}, down={len(down)}")
    p_up = sum(r["pressure"] for r in up) / len(up)
    p_down = sum(r["pressure"] for r in down) / len(down)
    station_length = 0.80 * length
    return {
        "velocity_m_s": velocity,
        "pressure_drop_pa": p_up - p_down,
        "pressure_gradient_pa_m": (p_up - p_down) / station_length,
        "mass_flow_per_depth_kg_m_s": rho * velocity * height,
        "mesh": mesh_stats,
        "zone_state": zone_state,
        "field_rows": rows,
        "files": [str(p.resolve()) for p in (mesh, raw, cas)],
    }


def ap(path: Path) -> str:
    return apdl_path(path.with_suffix(""))


__all__ = [
    "POROUS_LOGS", "POROUS_OUT", "ROOT", "ap", "case_paths", "clean_case",
    "classify_solver_error", "ensure_dirs", "finite_tree", "fluent_session", "relative_error",
    "run_apdl", "solve_porous_channel", "status_payload", "svg_plot", "write_json",
]
