"""Validate Case L raw Lagrangian tables and derived Eulerian projections."""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
DEFAULT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "sph_free_surface" / "case_l_dataset"
REQUIRED = {
    "time_s", "element_id", "position_x_m", "position_y_m", "position_z_m",
    "velocity_x_m_per_s", "velocity_y_m_per_s", "velocity_z_m_per_s",
    "pressure_pa", "density_kg_per_m3", "mass_kg",
}


def is_finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_case(case):
    errors = []
    table = Path(case["particle_table"])
    metadata = Path(case["particle_table_metadata"])
    rows = list(csv.DictReader(table.open(encoding="utf-8"))) if table.is_file() else []
    if not rows:
        errors.append("missing or empty raw particle table")
    if not metadata.is_file():
        errors.append("missing raw-table metadata")
    missing = REQUIRED - set(rows[0] if rows else [])
    if missing:
        errors.append(f"missing columns: {sorted(missing)}")
    times = [float(row["time_s"]) for row in rows if is_finite(row.get("time_s"))]
    if times != sorted(times):
        errors.append("time ordering is not nondecreasing")
    seen = set()
    mass_by_time = {}
    densities = []
    for row_number, row in enumerate(rows, start=2):
        key = (row.get("time_s"), row.get("element_id"))
        if key in seen:
            errors.append(f"duplicate element ID at row {row_number}")
        seen.add(key)
        for column in REQUIRED - {"element_id"}:
            if not is_finite(row.get(column)):
                errors.append(f"row {row_number}: non-finite {column}")
                break
        if is_finite(row.get("mass_kg")) and float(row["mass_kg"]) <= 0:
            errors.append(f"row {row_number}: non-positive mass")
        if is_finite(row.get("time_s")) and is_finite(row.get("mass_kg")):
            t = float(row["time_s"])
            mass_by_time[t] = mass_by_time.get(t, 0.0) + float(row["mass_kg"])
        if is_finite(row.get("density_kg_per_m3")):
            densities.append(float(row["density_kg_per_m3"]))
    masses = list(mass_by_time.values())
    mass_drift = (max(masses)-min(masses))/max(masses[0], 1e-30) if masses else math.inf
    if mass_drift >= 0.01:
        errors.append(f"relative mass drift {mass_drift:.6g} is not below 1%")
    if not densities or min(densities) < 0.90*998.2 or max(densities) > 1.10*998.2:
        errors.append("density outside +/-10% water reference range")
    if metadata.is_file():
        metadata_payload = json.loads(metadata.read_text(encoding="utf-8"))
        required_units = {"time", "position", "velocity", "pressure", "density", "mass"}
        if metadata_payload.get("representation") != "ragged_lagrangian_sph":
            errors.append("incorrect raw representation metadata")
        if not required_units <= set(metadata_payload.get("units", {})):
            errors.append("incomplete raw-data units metadata")
    projection_path = Path(case["eulerian_projection"]["path"])
    if not projection_path.is_file():
        errors.append("missing Eulerian projection")
        projection_shape = []
    else:
        with np.load(projection_path) as data:
            field = data["field"]
            projection_shape = list(field.shape)
            if field.ndim != 4 or field.shape[-1] != 4 or not np.isfinite(field).all():
                errors.append("invalid/non-finite projected field")
            if not np.array_equal(data["channels"], np.array(["velocity_x", "velocity_z", "pressure", "occupancy"])):
                errors.append("unexpected projection channels")
            occupancy = field[..., 3]
            if occupancy.size and (occupancy.min() < 0.0 or occupancy.max() > 1.0):
                errors.append("occupancy outside [0,1]")
            coverage = data["coverage_fraction"]
            if not np.isfinite(coverage).all() or np.any(coverage < 0.0) or np.any(coverage > 1.0):
                errors.append("invalid interpolation coverage")
            if field.shape[0] != len(data["time_s"]):
                errors.append("projection time/field shape mismatch")
    return {"case_id": case.get("case_id"), "status": "PASS" if not errors else "FAIL", "row_count": len(rows), "time_count": len(mass_by_time), "relative_mass_drift": mass_drift, "density_range_kg_m3": [min(densities),max(densities)] if densities else [], "projection_shape": projection_shape, "errors": errors}


def validate(dataset):
    index_path = dataset / "dataset_index.json"
    if not index_path.is_file():
        return {"status": "FAIL", "errors": [f"missing {index_path}"]}
    index = json.loads(index_path.read_text(encoding="utf-8"))
    cases = index.get("cases", [])
    case_results = [validate_case(case) for case in cases]
    errors = []
    if not 10 <= len(cases) <= 20:
        errors.append(f"case count {len(cases)} outside 10..20")
    if any(item["status"] != "PASS" for item in case_results):
        errors.append("one or more cases failed")
    required_index_units = {"time", "length", "velocity", "pressure", "density", "mass", "viscosity"}
    if not required_index_units <= set(index.get("units", {})):
        errors.append("dataset index has incomplete units metadata")
    report = {"status": "PASS" if not errors else "FAIL", "case_count": len(cases), "case_results": case_results, "errors": errors}
    (dataset / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", type=Path, default=DEFAULT)
    args = parser.parse_args()
    report = validate(args.dataset.resolve())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
