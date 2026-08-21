"""Canonical NPZ + JSON field export for Fluent and MAPDL porous cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def export_npz(path: Path, *, coordinates, connectivity=None, time=None,
               fields: dict[str, Any], metadata: dict[str, Any]) -> Path:
    arrays: dict[str, Any] = {"coordinates": np.asarray(coordinates, dtype=float)}
    if connectivity is not None:
        arrays["connectivity"] = np.asarray(connectivity, dtype=np.int64)
    if time is not None:
        arrays["time"] = np.asarray(time, dtype=float)
    arrays.update({name: np.asarray(value, dtype=float) for name, value in fields.items()})
    arrays["metadata_json"] = np.asarray(json.dumps(metadata, ensure_ascii=False))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    path.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def export_fluent_rows(path: Path, rows: list[dict[str, float]], *, metadata: dict[str, Any]) -> Path:
    ordered = sorted(
        {(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in rows}.values(),
        key=lambda r: (r["x-coordinate"], r["y-coordinate"]),
    )
    coordinates = [[r["x-coordinate"], r["y-coordinate"]] for r in ordered]
    mapping = {
        "pressure": "pressure", "velocity_x": "x-velocity", "velocity_y": "y-velocity",
        "temperature": "temperature", "porosity": "porosity",
    }
    fields = {out: [r[src] for r in ordered] for out, src in mapping.items() if src in ordered[0]}
    return export_npz(path, coordinates=coordinates, fields=fields, metadata=metadata)


def export_mapdl_transient(path: Path, *, coordinates, connectivity, time,
                           pore_pressure, displacement, stress, effective_stress,
                           metadata: dict[str, Any], temperature=None) -> Path:
    fields = {
        "pore_pressure": pore_pressure,
        "displacement": displacement,
        "stress": stress,
        "effective_stress": effective_stress,
    }
    if temperature is not None:
        fields["temperature"] = temperature
    return export_npz(path, coordinates=coordinates, connectivity=connectivity, time=time,
                      fields=fields, metadata=metadata)
