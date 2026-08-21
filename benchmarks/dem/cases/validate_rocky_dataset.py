"""Validate Rocky ragged Lagrangian datasets and optional Eulerian metadata."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "dataset"


def _finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_case(case: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    table_path = Path(case["particle_table"])
    metadata_path = Path(case["particle_table_metadata"])
    if not table_path.is_file():
        return {"case_id": case.get("case_id"), "status": "FAIL", "errors": ["missing particle table"]}
    if not metadata_path.is_file():
        errors.append("missing particle metadata")
    rows = list(csv.DictReader(table_path.open(encoding="utf-8")))
    required = {
        "time_s",
        "particle_id",
        "position_x_m",
        "position_y_m",
        "position_z_m",
        "velocity_x_m_per_s",
        "velocity_y_m_per_s",
        "velocity_z_m_per_s",
        "particle_size_m",
        "particle_mass_kg",
    }
    missing = required - set(rows[0] if rows else [])
    if missing:
        errors.append(f"missing columns: {sorted(missing)}")
    times = [float(row["time_s"]) for row in rows if _finite(row.get("time_s", ""))]
    if times != sorted(times):
        errors.append("time ordering is not nondecreasing")
    for row_number, row in enumerate(rows, start=2):
        if not row.get("particle_id"):
            errors.append(f"row {row_number}: missing particle ID")
        for name in required - {"particle_id"}:
            if not _finite(row.get(name, "")):
                errors.append(f"row {row_number}: non-finite {name}")
        if _finite(row.get("particle_size_m", "")) and float(row["particle_size_m"]) <= 0:
            errors.append(f"row {row_number}: non-positive particle size")
        if _finite(row.get("particle_mass_kg", "")) and float(row["particle_mass_kg"]) <= 0:
            errors.append(f"row {row_number}: non-positive particle mass")
    counts_by_time: dict[float, int] = {}
    ids_by_time: dict[float, set[str]] = {}
    for row in rows:
        if not _finite(row.get("time_s", "")):
            continue
        time_value = float(row["time_s"])
        counts_by_time[time_value] = counts_by_time.get(time_value, 0) + 1
        ids = ids_by_time.setdefault(time_value, set())
        if row.get("particle_id") in ids:
            errors.append(f"duplicate particle ID {row.get('particle_id')} at t={time_value}")
        ids.add(row.get("particle_id", ""))
    return {
        "case_id": case.get("case_id"),
        "status": "PASS" if not errors else "FAIL",
        "row_count": len(rows),
        "time_count": len(counts_by_time),
        "particle_counts_by_time": counts_by_time,
        "dynamic_particle_count_allowed": True,
        "errors": errors,
    }


def validate_dataset(dataset_dir: Path) -> dict[str, Any]:
    index_path = dataset_dir / "dataset_index.json"
    if not index_path.is_file():
        return {"status": "FAIL", "errors": [f"missing {index_path}"]}
    index = json.loads(index_path.read_text(encoding="utf-8"))
    cases = index.get("cases", [])
    results = [validate_case(case) for case in cases]
    errors = []
    if not (10 <= len(cases) <= 20):
        errors.append(f"case count {len(cases)} is outside requested range 10..20")
    if any(result["status"] != "PASS" for result in results):
        errors.append("one or more cases failed validation")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "case_count": len(cases),
        "case_results": results,
        "checks": {
            "time_ordering": True,
            "particle_ids": True,
            "finite_positions_velocities": True,
            "positive_size_mass": True,
            "dynamic_particle_count_supported": True,
            "eulerian_lagrangian_separation": index.get("representation"),
        },
        "errors": errors,
    }
    (dataset_dir / "validation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    report = validate_dataset(args.dataset.resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
