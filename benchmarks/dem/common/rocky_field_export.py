"""Eulerian/Lagrangian field exporters used inside Rocky PrePost scripts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PARTICLE_FIELDS = {
    "particle_id": "Particle ID",
    "particle_type": "Particle Type",
    "particle_inlet": "Particle Inlet",
    "position_x_m": "Coordinate : X",
    "position_y_m": "Coordinate : Y",
    "position_z_m": "Coordinate : Z",
    "velocity_x_m_per_s": "Velocity : Translational : X",
    "velocity_y_m_per_s": "Velocity : Translational : Y",
    "velocity_z_m_per_s": "Velocity : Translational : Z",
    "angular_velocity_x_rad_per_s": "Velocity : Rotational : X",
    "angular_velocity_y_rad_per_s": "Velocity : Rotational : Y",
    "angular_velocity_z_rad_per_s": "Velocity : Rotational : Z",
    "orientation_angle_rad": "Orientation : Angle",
    "orientation_axis_x": "Orientation : Vector : X",
    "orientation_axis_y": "Orientation : Vector : Y",
    "orientation_axis_z": "Orientation : Vector : Z",
    "particle_size_m": "Particle Size",
    "particle_mass_kg": "Particle Mass",
    "temperature_k": "Temperature",
}


def _values_at(grid_function, time_step):
    grid_function.SetCurrentTimeStep(time_step)
    return grid_function.GetArray().tolist()


def export_particle_table(study, destination: str | Path) -> dict:
    """Export a ragged Lagrangian particle table without mesh projection."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    particles = study.GetParticles()
    available = set(particles.GetGridFunctionNames())
    selected = {
        column: particles.GetGridFunction(name)
        for column, name in PARTICLE_FIELDS.items()
        if name in available
    }
    time_set = study.GetTimeSet()
    time_steps = list(time_set.GetTimeSteps())
    time_values = [float(value) for value in time_set.GetValues("s")]
    row_count = 0
    particle_counts = []
    with path.open("w", newline="", encoding="utf-8") as stream:
        fieldnames = ["time_s", *selected.keys()]
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for time_value, time_step in zip(time_values, time_steps):
            values = {
                column: _values_at(grid_function, time_step)
                for column, grid_function in selected.items()
            }
            count = max((len(item) for item in values.values()), default=0)
            particle_counts.append(count)
            for index in range(count):
                row = {"time_s": time_value}
                for column, items in values.items():
                    row[column] = items[index] if index < len(items) else ""
                writer.writerow(row)
                row_count += 1
    metadata = {
        "representation": "ragged_lagrangian_table",
        "projection_to_cfd_mesh": False,
        "path": str(path),
        "fields": list(selected),
        "time_values_s": time_values,
        "particle_counts": particle_counts,
        "row_count": row_count,
    }
    path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return metadata


def write_eulerian_metadata(destination: str | Path, metadata: dict) -> None:
    """Persist CFD mesh/field provenance separately from particle states."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"representation": "eulerian_mesh_fields", **metadata}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
