"""Shared utilities and reduced-order references for phase/reactive smoke tests."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "phase_reactive"
LOGS = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs")) / "phase_reactive"
DATA = OUT / "datasets"
FLUENT_VERSION = "Ansys Fluent Student 2026 R1 / 261"


def ensure_dirs() -> None:
    for path in (OUT, LOGS, DATA):
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    def convert(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Unsupported JSON value: {type(value).__name__}")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=convert), encoding="utf-8")
    return path


def base_payload(case: str, title: str, solver: str) -> dict[str, Any]:
    return {
        "case": case,
        "title": title,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "solver": solver,
        "status": "FAIL",
    }


def liquid_fraction(temperature: np.ndarray, solidus: float, liquidus: float) -> np.ndarray:
    return np.clip((np.asarray(temperature) - solidus) / (liquidus - solidus), 0.0, 1.0)


def specific_enthalpy(
    temperature: np.ndarray, *, reference_temperature: float, cp: float,
    latent_heat: float, solidus: float, liquidus: float,
) -> np.ndarray:
    return cp * (np.asarray(temperature) - reference_temperature) + latent_heat * liquid_fraction(
        temperature, solidus, liquidus
    )


def structured_quad_mesh(xs: np.ndarray, ys: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Coordinates are x-major and connectivity is zero-based."""
    coords = np.asarray([(x, y) for x in xs for y in ys], dtype=np.float64)
    ny = len(ys)
    nid = lambda i, j: i * ny + j
    conn = np.asarray(
        [(nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1))
         for i in range(len(xs) - 1) for j in range(len(ys) - 1)],
        dtype=np.int64,
    )
    return coords, conn


def finite_and_bounded(values: np.ndarray, lower: float, upper: float, tol: float = 1e-10) -> bool:
    a = np.asarray(values)
    return bool(np.isfinite(a).all() and a.min() >= lower - tol and a.max() <= upper + tol)


def relative_error(actual: float, reference: float) -> float:
    return abs(actual - reference) / max(abs(reference), 1e-30)


def first_order_plug_profile(x: np.ndarray, *, velocity: float, rate_constant: float) -> tuple[np.ndarray, np.ndarray]:
    ya = np.exp(-rate_constant * np.asarray(x) / velocity)
    return ya, 1.0 - ya


def gaussian_moving_temperature(
    x: np.ndarray, y: np.ndarray, *, power: float, speed: float, absorptivity: float,
    conductivity: float, ambient_temperature: float, source_x: float, beam_radius: float,
) -> np.ndarray:
    """Rosenthal-like regularized moving-source temperature benchmark."""
    dx = np.asarray(x) - source_x
    r = np.sqrt(dx * dx + np.asarray(y) ** 2 + beam_radius**2)
    advective = np.exp(-np.maximum(dx, 0.0) * speed / max(2.0e-5, 1e-30))
    rise = absorptivity * power * advective / (2.0 * math.pi * conductivity * r)
    return ambient_temperature + rise
