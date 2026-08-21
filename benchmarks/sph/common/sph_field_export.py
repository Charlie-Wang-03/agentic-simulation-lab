"""Export native SPH Lagrangian data and optional Cartesian projections."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


SPH_FIELDS = {
    "element_id": "Element ID",
    "position_x_m": "Coordinate : X",
    "position_y_m": "Coordinate : Y",
    "position_z_m": "Coordinate : Z",
    "velocity_x_m_per_s": "Velocity : X",
    "velocity_y_m_per_s": "Velocity : Y",
    "velocity_z_m_per_s": "Velocity : Z",
    "pressure_pa": "Pressure",
    "density_kg_per_m3": "Density",
    "mass_kg": "Mass",
    "temperature_k": "Temperature",
    "apparent_viscosity_pa_s": "Apparent Viscosity",
}


def _array(grid_function, time_step):
    grid_function.SetCurrentTimeStep(time_step)
    values = grid_function.GetArray()
    return [] if values is None else values.tolist()


def read_sph_steps(study):
    sph = study.GetSphSettings()
    available = set(sph.GetGridFunctionNames())
    selected = {column: sph.GetGridFunction(name) for column, name in SPH_FIELDS.items() if name in available}
    time_set = study.GetTimeSet()
    if time_set is None:
        return [], {"available_grid_functions": sorted(available), "selected_fields": list(selected)}
    time_steps = list(time_set.GetTimeSteps())
    time_values = [float(v) for v in time_set.GetValues("s")]
    steps = []
    for time_value, time_step in zip(time_values, time_steps):
        arrays = {column: _array(function, time_step) for column, function in selected.items()}
        count = max((len(values) for values in arrays.values()), default=0)
        rows = []
        for index in range(count):
            row = {"time_s": time_value}
            for column, values in arrays.items():
                row[column] = values[index] if index < len(values) else math.nan
            rows.append(row)
        steps.append((time_value, rows))
    return steps, {"available_grid_functions": sorted(available), "selected_fields": list(selected)}


def export_lagrangian(study, destination: str | Path) -> dict:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    steps, info = read_sph_steps(study)
    fields = ["time_s", *info["selected_fields"]]
    row_count = 0
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for _, rows in steps:
            writer.writerows(rows)
            row_count += len(rows)
    metadata = {
        "representation": "ragged_lagrangian_sph",
        "path": str(path),
        "time_values_s": [time for time, _ in steps],
        "element_counts": [len(rows) for _, rows in steps],
        "row_count": row_count,
        "units": {
            "time": "s", "position": "m", "velocity": "m/s", "pressure": "Pa",
            "density": "kg/m3", "mass": "kg", "temperature": "K",
        },
        **info,
    }
    path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def project_xz_to_npz(study, destination: str | Path, *, xlim, zlim, shape=(61, 31), smoothing_length_m=0.02):
    """Kernel-project SPH samples to field[time,z,x,channel], retaining raw data separately."""
    import numpy as np

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    steps, _ = read_sph_steps(study)
    nx, nz = int(shape[0]), int(shape[1])
    xs = np.linspace(float(xlim[0]), float(xlim[1]), nx)
    zs = np.linspace(float(zlim[0]), float(zlim[1]), nz)
    channels = ["velocity_x", "velocity_z", "pressure", "occupancy"]
    field = np.zeros((len(steps), nz, nx, len(channels)), dtype=np.float32)
    coverage = []
    radius = 2.0 * float(smoothing_length_m)
    for ti, (_, rows) in enumerate(steps):
        covered = 0
        for iz, z in enumerate(zs):
            for ix, x in enumerate(xs):
                weighted = [0.0, 0.0, 0.0]
                weight_sum = 0.0
                for row in rows:
                    dx = x - float(row.get("position_x_m", math.nan))
                    dz = z - float(row.get("position_z_m", math.nan))
                    r = math.hypot(dx, dz)
                    if not math.isfinite(r) or r >= radius:
                        continue
                    q = r / radius
                    weight = (1.0 - q) ** 3
                    weighted[0] += weight * float(row.get("velocity_x_m_per_s", 0.0))
                    weighted[1] += weight * float(row.get("velocity_z_m_per_s", 0.0))
                    weighted[2] += weight * float(row.get("pressure_pa", 0.0))
                    weight_sum += weight
                if weight_sum > 0.0:
                    field[ti, iz, ix, :3] = np.asarray(weighted) / weight_sum
                    field[ti, iz, ix, 3] = min(1.0, weight_sum)
                    covered += 1
        coverage.append(covered / float(nx * nz))
    np.savez_compressed(
        path,
        field=field,
        time_s=np.asarray([time for time, _ in steps]),
        x_m=xs,
        z_m=zs,
        channels=np.asarray(channels),
        coverage_fraction=np.asarray(coverage),
    )
    return {"path": str(path), "shape": list(field.shape), "channels": channels, "coverage_fraction": coverage}
