"""Independent integrity and physics checks for the electrostatic NPZ dataset."""

from __future__ import annotations

import json
import math

import numpy as np

from aedt_smoke_common import OUTPUT_ROOT, utc_now, write_json


def main() -> int:
    folder = OUTPUT_ROOT / "dataset_electrostatic_10"
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    archive = np.load(folder / "electrostatic_voltage_sweep.npz", allow_pickle=False)
    nodes = archive["nodes_m"]
    cells = archive["connectivity_quads"]
    params = archive["parameters_voltage_V"][:, 0]
    efield = archive["field_E_magnitude_V_per_m"]
    potential = archive["field_potential_V"]
    labels = archive["labels_mean_max_E_V_per_m"]
    normalized_mean = labels[:, 0] / params
    checks = {
        "metadata_pass": metadata.get("status") == "PASS",
        "exactly_ten_samples": len(params) == 10,
        "shapes_consistent": efield.shape == potential.shape == (10, len(nodes)) and labels.shape == (10, 2),
        "all_arrays_finite": all(np.isfinite(a).all() for a in (nodes, cells, params, efield, potential, labels)),
        "connectivity_in_range": int(cells.min()) >= 0 and int(cells.max()) < len(nodes),
        "strictly_increasing_voltage": bool(np.all(np.diff(params) > 0)),
        "mean_field_strictly_increasing": bool(np.all(np.diff(labels[:, 0]) > 0)),
        "linear_scaling_with_voltage": float(np.ptp(normalized_mean) / np.mean(normalized_mean)) < 0.02,
        "potential_bounds_track_excitation": bool(np.all(potential.min(axis=1) >= -1e-6) and np.all(potential.max(axis=1) <= params * 1.01)),
    }
    report = {"name": "Electrostatic dataset validation", "timestamp_utc": utc_now(), "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "metrics": {"nodes": int(len(nodes)), "quad_cells": int(len(cells)), "normalized_mean_E_range": [float(normalized_mean.min()), float(normalized_mean.max())], "normalized_mean_E_relative_span": float(np.ptp(normalized_mean) / np.mean(normalized_mean))}}
    write_json(folder / "validation.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
