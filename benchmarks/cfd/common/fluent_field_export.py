"""Reusable numerical field export and validation for Fluent smoke tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from fluent_smoke_common import read_fluent_ascii_export


ALIASES = {
    "x": "x-coordinate", "y": "y-coordinate", "z": "z-coordinate",
    "velocity_x": "x-velocity", "velocity_y": "y-velocity", "velocity_z": "z-velocity",
    "pressure": "pressure", "temperature": "temperature", "density": "density",
    "velocity_magnitude": "velocity-magnitude",
    "turbulent_kinetic_energy": "turb-kinetic-energy",
    "turbulent_dissipation_rate": "turb-diss-rate",
    "specific_dissipation_rate": "specific-diss-rate",
    "vorticity": "vorticity-magnitude",
    "wall_y_plus": "wall-yplus",
    "volume_fraction": "volume-fraction",
}


def rows_to_arrays(rows: list[dict[str, float]], fields: list[str]) -> dict[str, np.ndarray]:
    """Deduplicate nodal ASCII rows and return consistently ordered arrays."""
    coord_keys = [k for k in ("x-coordinate", "y-coordinate", "z-coordinate") if any(k in r for r in rows)]
    if len(coord_keys) < 2:
        raise ValueError("At least x/y coordinates are required")
    unique: dict[tuple[float, ...], dict[str, float]] = {}
    for row in rows:
        if all(k in row for k in coord_keys):
            key = tuple(round(row[k], 13) for k in coord_keys)
            if key not in unique:
                unique[key] = row.copy()
            else:
                unique[key].update(row)
    ordered = [unique[k] for k in sorted(unique)]
    out = {"coordinates": np.asarray([[r[k] for k in coord_keys] for r in ordered], dtype=np.float64)}
    for name in fields:
        source = ALIASES.get(name, name)
        out[name] = np.asarray([r.get(source, np.nan) for r in ordered], dtype=np.float64)
    return out


def export_npz_from_ascii(
    ascii_path: Path,
    npz_path: Path,
    *,
    fields: list[str],
    metadata: dict[str, Any],
    connectivity: np.ndarray | None = None,
    time: float | None = None,
) -> dict[str, Any]:
    arrays = rows_to_arrays(read_fluent_ascii_export(ascii_path), fields)
    if connectivity is not None:
        arrays["connectivity"] = np.asarray(connectivity, dtype=np.int64)
    if time is not None:
        arrays["time"] = np.asarray(time, dtype=np.float64)
    arrays["metadata_json"] = np.asarray(json.dumps(metadata, ensure_ascii=False))
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(npz_path, **arrays)
    check = validate_npz(npz_path, required=["coordinates", *fields])
    return {"path": str(npz_path.resolve()), **check}


def validate_npz(path: Path, *, required: list[str]) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        missing = [k for k in required if k not in data]
        shapes = {k: list(data[k].shape) for k in data.files if k != "metadata_json"}
        finite = {
            k: bool(np.isfinite(data[k]).all())
            for k in data.files
            if data[k].dtype.kind in "fci"
        }
        metadata_ok = False
        if "metadata_json" in data:
            try:
                metadata_ok = isinstance(json.loads(str(data["metadata_json"])), dict)
            except Exception:
                metadata_ok = False
    return {
        "missing": missing,
        "shapes": shapes,
        "all_finite": all(finite.values()),
        "metadata_valid": metadata_ok,
        "valid": not missing and all(finite.values()) and metadata_ok,
    }


def stack_time_series_npz(
    snapshot_paths: list[Path], output_path: Path, *, fields: list[str], metadata: dict[str, Any]
) -> dict[str, Any]:
    """Stack compatible per-time NPZ snapshots into field[time,node]."""
    times=[]; coords=None; stacks={k:[] for k in fields}
    for path in snapshot_paths:
        with np.load(path,allow_pickle=False) as data:
            c=np.asarray(data["coordinates"])
            if coords is None: coords=c.copy()
            elif c.shape!=coords.shape or not np.allclose(c,coords,rtol=0,atol=1e-11):
                raise ValueError(f"inconsistent coordinates: {path}")
            times.append(float(np.asarray(data["time"])))
            for key in fields: stacks[key].append(np.asarray(data[key]))
    order=np.argsort(times); arrays={"coordinates":coords,"time":np.asarray(times)[order]}
    for key,values in stacks.items(): arrays[key]=np.stack(values,axis=0)[order]
    arrays["metadata_json"]=np.asarray(json.dumps(metadata,ensure_ascii=False))
    output_path.parent.mkdir(parents=True,exist_ok=True); np.savez_compressed(output_path,**arrays)
    check=validate_npz(output_path,required=["coordinates","time",*fields])
    check["time_strictly_increasing"]=bool(np.all(np.diff(arrays["time"])>0))
    check["valid"]=check["valid"] and check["time_strictly_increasing"]
    return {"path":str(output_path.resolve()),**check}
