"""Neural-operator-oriented field writers for phase change and reactive flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def _save(path: Path, arrays: dict[str, Any], metadata: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {name: np.asarray(value) for name, value in arrays.items()}
    values["metadata_json"] = np.asarray(json.dumps(metadata, ensure_ascii=False))
    np.savez_compressed(path, **values)
    return path


def save_phase_change(
    path: Path, *, coordinates: np.ndarray, connectivity: np.ndarray, time: np.ndarray,
    temperature: np.ndarray, liquid_fraction: np.ndarray,
    velocity_x: np.ndarray | None = None, velocity_y: np.ndarray | None = None,
    global_quantities: dict[str, Any] | None = None, metadata: dict[str, Any],
) -> Path:
    arrays: dict[str, Any] = {
        "coordinates": coordinates, "connectivity": connectivity, "time": time,
        "temperature": temperature, "liquid_fraction": liquid_fraction,
    }
    if velocity_x is not None:
        arrays["velocity_x"] = velocity_x
    if velocity_y is not None:
        arrays["velocity_y"] = velocity_y
    for key, value in (global_quantities or {}).items():
        arrays[key] = value
    return _save(path, arrays, metadata)


def save_reactive_flow(
    path: Path, *, coordinates: np.ndarray, connectivity: np.ndarray,
    velocity_x: np.ndarray, velocity_y: np.ndarray, pressure: np.ndarray,
    temperature: np.ndarray, species: dict[str, np.ndarray], reaction_rate: np.ndarray,
    heat_release_rate: np.ndarray, metadata: dict[str, Any], time: np.ndarray | None = None,
) -> Path:
    arrays: dict[str, Any] = {
        "coordinates": coordinates, "connectivity": connectivity,
        "velocity_x": velocity_x, "velocity_y": velocity_y, "pressure": pressure,
        "temperature": temperature, "reaction_rate": reaction_rate,
        "heat_release_rate": heat_release_rate,
    }
    if time is not None:
        arrays["time"] = time
    for name, values in species.items():
        arrays[f"species_{name}"] = values
    return _save(path, arrays, metadata)
