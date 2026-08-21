"""Revalidate migrated JSON and NPZ evidence without launching a solver."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "artifacts" / "legacy" / "outputs"


def finite(value: object) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite(item) for item in value.values())
    if isinstance(value, list):
        return all(finite(item) for item in value)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", action="store_true")
    args = parser.parse_args()
    json_errors: list[str] = []
    qualifications: list[str] = []
    allowed_json_nonfinite = {
        "sph_free_surface/case_d_jet_impact/result.json": "native wall-force scalar unavailable; validated pressure distribution and momentum force are finite",
        "sph_free_surface/case_h_rigid_body/result.json": "initial pressure is undefined before the first populated fluid sample; validated force history is finite",
    }
    json_files = list(LEGACY.rglob("*.json"))
    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not finite(data):
                relative = path.relative_to(LEGACY).as_posix()
                if relative in allowed_json_nonfinite:
                    qualifications.append(f"{relative}: {allowed_json_nonfinite[relative]}")
                else:
                    json_errors.append(f"non-finite: {relative}")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            json_errors.append(f"parse: {path.relative_to(LEGACY).as_posix()}: {exc}")
    npz_files = list(LEGACY.rglob("*.npz")) if args.npz else []
    npz_errors: list[str] = []
    if args.npz:
        import numpy as np
        for path in npz_files:
            try:
                with np.load(path, allow_pickle=False) as archive:
                    for name in archive.files:
                        array = archive[name]
                        if array.dtype.kind in "fc" and not np.isfinite(array).all():
                            relative = path.relative_to(LEGACY).as_posix()
                            if relative == "sph_free_surface/case_b_dam_break/eulerian_projection.npz" and name == "field":
                                qualifications.append(f"{relative}:{name}: NaN marks uncovered Eulerian projection cells")
                            else:
                                npz_errors.append(f"non-finite: {relative}:{name}")
            except (OSError, ValueError) as exc:
                npz_errors.append(f"load: {path.relative_to(LEGACY).as_posix()}: {exc}")
    result = {
        "status": "PASS" if not json_errors and not npz_errors else "FAIL",
        "json_files": len(json_files), "npz_files": len(npz_files),
        "json_errors": json_errors, "npz_errors": npz_errors, "qualifications": qualifications,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
