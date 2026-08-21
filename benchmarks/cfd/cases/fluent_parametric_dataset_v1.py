"""Implementation of the Fluent flagship Dataset Contract v1 workflow."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import ansys.fluent.core as pyfluent
import numpy as np
from fluent_field_export import export_npz_from_ascii
from fluent_mesh import rectangular_2d
from fluent_smoke_common import OUT, fluent_session, read_fluent_ascii_export, svg_xy_plot, write_csv, write_json

from agentic_simulation_lab.datasets import sha256_file, validate_dataset

DATA = OUT / "fluent_dataset"
RESULT = Path(os.environ.get("AGENTIC_SIM_RESULT_FILE", OUT / "case-result.json"))
REYNOLDS_NUMBERS = (100, 150, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200)
GRID_CELLS_PER_SIDE = 40


def _observed_fluent_version(session: object) -> str:
    getter = getattr(session, "get_fluent_version", None)
    if callable(getter):
        try:
            observed = getter()
            if observed:
                return str(observed)
        except Exception:  # noqa: BLE001 - optional version API failures must not invent provenance
            return "unknown"
    return "unknown"


def _relative(path: Path) -> str:
    return path.relative_to(OUT).as_posix()


def _descriptor(
    index: list[dict[str, object]], observed_version: str, index_path: Path, plot_path: Path
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dataset_id": "cfd/fluent-parametric-dataset",
        "name": "Fluent lid-driven-cavity parametric educational dataset",
        "source": {
            "case": "cfd/fluent-parametric-dataset",
            "physics_domain": "cfd",
            "problem": "Steady two-dimensional laminar lid-driven cavity",
        },
        "representation": {
            "kind": "eulerian_field",
            "mesh": "structured_quadrilateral",
            "temporal": "steady",
        },
        "parameters": [
            {
                "name": "reynolds_number",
                "units": "1",
                "meaning": "Ratio of inertial to viscous forces based on lid velocity and cavity length",
                "values": list(REYNOLDS_NUMBERS),
                "provenance": "deterministic educational smoke sweep",
            },
            {
                "name": "lid_velocity_m_s",
                "units": "m/s",
                "meaning": "Tangential velocity of the moving top wall",
                "values": [1.0],
                "provenance": "generation configuration",
            },
            {
                "name": "cavity_length_m",
                "units": "m",
                "meaning": "Side length of the square cavity",
                "values": [1.0],
                "provenance": "generation configuration",
            },
        ],
        "fields": [
            {"name": "velocity_x", "units": "m/s", "location": "node", "dtype": "float64", "shape": ["node"]},
            {"name": "velocity_y", "units": "m/s", "location": "node", "dtype": "float64", "shape": ["node"]},
            {"name": "pressure", "units": "Pa", "location": "node", "dtype": "float64", "shape": ["node"]},
        ],
        "geometry": {
            "shared": True,
            "dimensionality": 2,
            "coordinates": {"array": "coordinates", "units": "m", "dtype": "float64", "shape": ["node", 2]},
            "connectivity": {
                "array": "connectivity",
                "location": "cell",
                "index_base": 0,
                "dtype": "int64",
                "shape": ["cell", 4],
            },
        },
        "samples": [
            {
                "id": str(item["case_id"]),
                "parameters": {
                    "reynolds_number": item["reynolds_number"],
                    "lid_velocity_m_s": item["lid_velocity_m_s"],
                    "cavity_length_m": item["cavity_length_m"],
                },
                "files": [
                    {
                        "path": str(item["npz_file"]),
                        "format": "npz",
                        "sha256": sha256_file(DATA / str(item["npz_file"])),
                    }
                ],
            }
            for item in index
        ],
        "provenance": {
            "generator": "benchmarks/cfd/cases/smoke_fluent_parametric_dataset.py",
            "source_case": "cfd/fluent-parametric-dataset",
            "solver": {
                "name": "Ansys Fluent",
                "requested_version": "2026 R1 / 261",
                "observed_version": observed_version,
            },
            "packages": {"ansys-fluent-core": pyfluent.__version__},
            "generation_configuration": {
                "profile": "fixed 12-sample educational smoke sweep",
                "iterations_requested_per_sample": 900,
                "grid_cells_per_side": GRID_CELLS_PER_SIDE,
                "precision": "double",
                "processor_count": 1,
            },
        },
        "validation": {
            "status": "NOT_RUN",
            "schema_reload": "NOT_RUN",
            "numerical_finiteness": "NOT_RUN",
            "shape_topology_consistency": "NOT_RUN",
            "physics": {
                "status": "PASS",
                "basis": "historical catalog evidence; not recomputed by Dataset Contract validation",
                "source_case": "cfd/fluent-parametric-dataset",
                "evidence": "benchmarks/cfd/references/historical_results.json",
            },
        },
        "splits": {
            "official": False,
            "assignments": {},
            "semantics": (
                "No official train/validation/test split. Twelve samples demonstrate a portable data pipeline; "
                "they are not a scientifically optimized or training-scale ML benchmark."
            ),
        },
        "supporting_files": [
            {"path": index_path.name, "role": "human-readable sample index", "sha256": sha256_file(index_path)},
            {"path": plot_path.name, "role": "diagnostic plot", "sha256": sha256_file(plot_path)},
        ],
    }


def _canonical_result(status: str, checks: dict[str, bool], metrics: dict[str, object], artifacts: list[str],
                      observed_version: str, error: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": 1,
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "artifacts": artifacts,
        "provenance": {
            "source_case": "cfd/fluent-parametric-dataset",
            "solver": {
                "name": "Ansys Fluent",
                "requested_version": "2026 R1 / 261",
                "observed_version": observed_version,
            },
            "packages": {"ansys-fluent-core": pyfluent.__version__},
        },
    }
    if error:
        result["error"] = error
    return result


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    evidence_dir = OUT / "solver-evidence"
    evidence_dir.mkdir(exist_ok=True)
    mesh = evidence_dir / "cavity_shared_mesh.msh"
    one_dimensional_coordinates = [
        0.5 * (1 - math.cos(math.pi * index / GRID_CELLS_PER_SIDE))
        for index in range(GRID_CELLS_PER_SIDE + 1)
    ]
    mesh_stats = rectangular_2d(
        mesh,
        one_dimensional_coordinates,
        one_dimensional_coordinates,
        left=("left-wall", "wall"),
        right=("right-wall", "wall"),
        bottom=("bottom-wall", "wall"),
        top=("lid", "wall"),
    )
    node_id = lambda i, j: i * (GRID_CELLS_PER_SIDE + 1) + j
    connectivity = np.asarray(
        [
            (node_id(i, j), node_id(i + 1, j), node_id(i + 1, j + 1), node_id(i, j + 1))
            for i in range(GRID_CELLS_PER_SIDE)
            for j in range(GRID_CELLS_PER_SIDE)
        ],
        dtype=np.int64,
    )
    index: list[dict[str, object]] = []
    vortex_curve: list[tuple[float, float]] = []
    observed_version = "unknown"
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=DATA) as session:
            observed_version = _observed_fluent_version(session)
            session.settings.file.read_mesh(file_name=str(mesh))
            session.settings.setup.models.viscous.model = "laminar"
            air = session.settings.setup.materials.fluid["air"]
            air.density.value = 1.0
            lid = session.settings.setup.boundary_conditions.wall["lid"]
            lid.momentum.wall_motion = "Moving Wall"
            lid.momentum.velocity_spec = "Components"
            lid.momentum.velocity_components[0].value = 1.0
            lid.momentum.velocity_components[1].value = 0.0
            surfaces = ["interior", "left-wall", "right-wall", "bottom-wall", "lid"]
            for sample_number, reynolds_number in enumerate(REYNOLDS_NUMBERS):
                air.viscosity.value = 1.0 / reynolds_number
                session.settings.solution.initialization.hybrid_initialize()
                session.settings.solution.run_calculation.iterate(iter_count=900)
                case_id = f"case_{sample_number:03d}_re{reynolds_number}"
                raw_path = DATA / f"{case_id}_raw.csv"
                npz_path = DATA / f"{case_id}.npz"
                session.settings.file.export.ascii(
                    file_name=str(raw_path),
                    surface_name_list=surfaces,
                    delimiter="comma",
                    quantities=[
                        "x-coordinate",
                        "y-coordinate",
                        "x-velocity",
                        "y-velocity",
                        "pressure",
                        "velocity-magnitude",
                    ],
                    location="node",
                )
                sample_metadata = {
                    "case_id": case_id,
                    "case_parameters": {
                        "reynolds_number": reynolds_number,
                        "lid_velocity_m_s": 1.0,
                        "cavity_length_m": 1.0,
                    },
                    "units": {"coordinates": "m", "velocity_x": "m/s", "velocity_y": "m/s", "pressure": "Pa"},
                    "mesh": {
                        "nodes": mesh_stats["nodes"],
                        "cells": mesh_stats["cells"],
                        "topology": "shared structured quadrilateral",
                    },
                    "provenance": {
                        "solver": "Ansys Fluent",
                        "requested_version": "2026 R1 / 261",
                        "observed_version": observed_version,
                        "ansys-fluent-core": pyfluent.__version__,
                    },
                    "solver_configuration": {
                        "type": "steady pressure-based",
                        "viscous_model": "laminar",
                        "iterations_requested": 900,
                    },
                }
                export_check = export_npz_from_ascii(
                    raw_path,
                    npz_path,
                    fields=["velocity_x", "velocity_y", "pressure"],
                    metadata=sample_metadata,
                    connectivity=connectivity,
                )
                rows = read_fluent_ascii_export(raw_path)
                unique = {
                    (round(row["x-coordinate"], 12), round(row["y-coordinate"], 12)): row for row in rows
                }
                values = list(unique.values())
                candidates = [
                    row
                    for row in values
                    if 0.15 < row["x-coordinate"] < 0.85 and 0.15 < row["y-coordinate"] < 0.9
                ]
                vortex_center = min(candidates, key=lambda row: row["velocity-magnitude"])
                kinetic_energy = float(
                    np.mean([0.5 * (row["x-velocity"] ** 2 + row["y-velocity"] ** 2) for row in values])
                )
                index.append(
                    {
                        "case_id": case_id,
                        "reynolds_number": reynolds_number,
                        "lid_velocity_m_s": 1.0,
                        "cavity_length_m": 1.0,
                        "npz_file": npz_path.name,
                        "nodes": export_check["shapes"]["coordinates"][0],
                        "cells": export_check["shapes"]["connectivity"][0],
                        "max_velocity_m_s": max(row["velocity-magnitude"] for row in values),
                        "mean_kinetic_energy_m2_s2": kinetic_energy,
                        "main_vortex_x": vortex_center["x-coordinate"],
                        "main_vortex_y": vortex_center["y-coordinate"],
                        "file_valid": export_check["valid"],
                    }
                )
                vortex_curve.append((float(reynolds_number), vortex_center["y-coordinate"]))
                raw_path.unlink(missing_ok=True)
            session.settings.file.write_case_data(file_name=str(evidence_dir / "last_case_re1200.cas.h5"))

        index_path = write_csv(DATA / "dataset_index.csv", list(index[0]), index)
        plot_path = svg_xy_plot(
            DATA / "vortex_position_vs_re.svg",
            vortex_curve,
            title="Case L: primary vortex y-position",
            xlabel="Re",
            ylabel="y/L",
        )
        descriptor_path = write_json(DATA / "dataset.json", _descriptor(index, observed_version, index_path, plot_path))
        first_validation = validate_dataset(DATA)
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        contract_status = first_validation["status"]
        descriptor["validation"].update(
            {
                "status": contract_status,
                "schema_reload": contract_status,
                "numerical_finiteness": contract_status,
                "shape_topology_consistency": contract_status,
            }
        )
        write_json(descriptor_path, descriptor)
        validation = validate_dataset(DATA)
        validation_path = write_json(DATA / "dataset_validation.json", validation)
        checks = {
            "case_count_12": len(index) == 12,
            "all_case_exports_valid": all(bool(item["file_valid"]) for item in index),
            "dataset_contract_v1_pass": validation["status"] == "PASS",
            "consistent_node_count": len({item["nodes"] for item in index}) == 1,
            "consistent_cell_count": len({item["cells"] for item in index}) == 1,
        }
        status = "PASS" if all(checks.values()) else "FAIL"
        result = _canonical_result(
            status,
            checks,
            {
                "sample_count": len(index),
                "reynolds_number_values": list(REYNOLDS_NUMBERS),
                "nodes_per_sample": index[0]["nodes"],
                "cells_per_sample": index[0]["cells"],
            },
            [_relative(path) for path in (descriptor_path, index_path, validation_path, plot_path)],
            observed_version,
        )
        result["provenance"]["dataset_descriptor"] = _relative(descriptor_path)
    except Exception as exc:  # noqa: BLE001 - case boundary records every failure in the canonical result
        result = _canonical_result("FAIL", {}, {}, [], observed_version, f"{type(exc).__name__}: {exc}")
    write_json(RESULT, result)
    print(result)
    return 0 if result["status"] == "PASS" else 1
