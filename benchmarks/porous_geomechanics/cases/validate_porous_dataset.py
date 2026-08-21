"""Validate canonical porous/geomechanics NPZ datasets and basic physics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from porous_geomechanics_common import POROUS_OUT, write_json


def validate_file(path: Path) -> dict:
    checks: dict[str, bool] = {}
    issues: list[str] = []
    with np.load(path, allow_pickle=False) as data:
        keys = set(data.files)
        checks["coordinates_present"] = "coordinates" in keys
        checks["metadata_present"] = "metadata_json" in keys
        numeric = [key for key in keys if key != "metadata_json"]
        checks["all_finite"] = all(np.isfinite(data[key]).all() for key in numeric)
        if "time" in keys:
            time = data["time"]
            checks["time_strictly_increasing"] = time.ndim == 1 and np.all(np.diff(time) > 0)
            nt = len(time)
            for key in ("pore_pressure", "displacement", "stress", "effective_stress", "temperature"):
                if key in keys:
                    checks[f"{key}_time_axis"] = data[key].shape[0] == nt
        if "pore_pressure" in keys and data["pore_pressure"].ndim >= 2:
            p = data["pore_pressure"]
            peak_abs = np.max(np.abs(p), axis=tuple(range(1, p.ndim)))
            checks["peak_pore_pressure_dissipates"] = peak_abs[-1] <= peak_abs[0] * 1.01
        if "displacement" in keys:
            checks["displacement_reasonable"] = float(np.max(np.abs(data["displacement"]))) < 1.0e3
        metadata = json.loads(str(data["metadata_json"])) if "metadata_json" in keys else {}
        checks["units_documented"] = bool(metadata.get("units"))
        checks["parameters_documented"] = bool(metadata.get("parameters") or metadata.get("model"))
        shape = {key: list(data[key].shape) for key in numeric}
    checks = {name: bool(passed) for name, passed in checks.items()}
    for name, passed in checks.items():
        if not passed:
            issues.append(name)
    return {"file": str(path.resolve()), "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks, "issues": issues, "shape": shape, "metadata": metadata}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or sorted(POROUS_OUT.glob("dataset_*/poromechanics_case.npz"))
    results = [validate_file(path) for path in paths]
    summary = {"status": "PASS" if results and all(r["status"] == "PASS" for r in results) else "FAIL",
               "case_count": len(results), "results": results}
    write_json(POROUS_OUT / "dataset_validation.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
