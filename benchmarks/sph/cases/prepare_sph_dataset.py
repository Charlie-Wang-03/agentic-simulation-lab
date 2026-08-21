"""Remove only solver-undefined snapshots from Case L and record the exclusion.

Rocky IISPH reports pressure as NaN at t=0 before its first pressure solve.
Filling those values would invent data, so the dataset starts at the first
fully defined output time and records the excluded time in every metadata file.
"""

import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
DATASET = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "sph_free_surface" / "case_l_dataset"
REQUIRED_NUMERIC = [
    "time_s", "position_x_m", "position_y_m", "position_z_m",
    "velocity_x_m_per_s", "velocity_y_m_per_s", "velocity_z_m_per_s",
    "pressure_pa", "density_kg_per_m3", "mass_kg",
]


def finite_row(row):
    try:
        return all(math.isfinite(float(row[name])) for name in REQUIRED_NUMERIC)
    except (KeyError, TypeError, ValueError):
        return False


index_path = DATASET / "dataset_index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
for case in index["cases"]:
    table_path = Path(case["particle_table"])
    metadata_path = Path(case["particle_table_metadata"])
    with table_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    grouped = {}
    for row in rows:
        grouped.setdefault(float(row["time_s"]), []).append(row)
    excluded = sorted(t for t, snapshot in grouped.items() if not snapshot or not all(finite_row(row) for row in snapshot))
    retained = [row for row in rows if float(row["time_s"]) not in excluded]
    with table_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(retained)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    retained_times = sorted({float(row["time_s"]) for row in retained})
    metadata["time_values_s"] = retained_times
    metadata["element_counts"] = [sum(float(row["time_s"]) == t for row in retained) for t in retained_times]
    metadata["row_count"] = len(retained)
    metadata["excluded_solver_undefined_time_values_s"] = excluded
    metadata["exclusion_reason"] = "Rocky IISPH pressure is undefined before the first pressure solve; values were not imputed."
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    projection_path = Path(case["eulerian_projection"]["path"])
    with np.load(projection_path) as data:
        payload = {name: data[name] for name in data.files}
    keep = np.asarray([float(t) not in excluded for t in payload["time_s"]], dtype=bool)
    payload["field"] = payload["field"][keep]
    payload["time_s"] = payload["time_s"][keep]
    payload["coverage_fraction"] = payload["coverage_fraction"][keep]
    np.savez_compressed(projection_path, **payload)
    case["eulerian_projection"]["shape"] = list(payload["field"].shape)
    case["eulerian_projection"]["coverage_fraction"] = payload["coverage_fraction"].tolist()
    case["excluded_solver_undefined_time_values_s"] = excluded
    case["element_counts"] = metadata["element_counts"]

index["data_quality_policy"] = "Snapshots containing solver-undefined required fields are excluded as whole snapshots; no imputation is performed."
index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
print(json.dumps({"status": "PASS", "case_count": len(index["cases"]), "excluded_time_s": sorted({t for case in index["cases"] for t in case.get("excluded_solver_undefined_time_values_s", [])})}, indent=2))
