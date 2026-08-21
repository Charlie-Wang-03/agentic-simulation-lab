"""Validate independently meshed Fluid -> Thermal -> Structural NPZ cases."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
from multiphysics_field_export import validate_multiphysics_case

REQUIRED_FIELDS = {
    "fluid": ["coordinates", "connectivity", "velocity", "pressure", "temperature"],
    "solid": ["coordinates", "connectivity", "temperature", "displacement", "equivalent_stress"],
    "interface": ["coordinates", "temperature", "heat_flux", "pressure"],
}
REQUIRED_PARAMS = {"inlet_velocity_m_s", "inlet_temperature_K", "solid_conductivity_W_mK",
                   "youngs_modulus_Pa", "wall_thickness_m"}
REQUIRED_UNITS = {"coordinates", "temperature", "velocity", "pressure", "heat_flux",
                  "displacement", "equivalent_stress", "time"}


def _case_checks(path: Path):
    base = validate_multiphysics_case(path)
    with np.load(path, allow_pickle=False) as d:
        meta = json.loads(str(d["metadata_json"]))
        missing_fields = [f"{domain}_{name}" for domain, names in REQUIRED_FIELDS.items()
                          for name in names if f"{domain}_{name}" not in d]
        node_shapes = all(d[f"{domain}_{name}"].shape[0] == len(d[f"{domain}_coordinates"])
                          for domain, names in REQUIRED_FIELDS.items() for name in names
                          if name not in ("connectivity",) and f"{domain}_{name}" in d)
        conn_ok = all(d[f"{domain}_connectivity"].ndim == 2 and
                      d[f"{domain}_connectivity"].min() >= 0 and
                      d[f"{domain}_connectivity"].max() < len(d[f"{domain}_coordinates"])
                      for domain in ("fluid", "solid"))
        temp_ok = all(np.all((d[k] > 200.) & (d[k] < 1000.))
                      for k in ("fluid_temperature", "solid_temperature", "interface_temperature") if k in d)
        response_ok = bool(np.linalg.norm(d["solid_displacement"], axis=1).max() > 0. and
                           d["solid_equivalent_stress"].max() > 0.) if not missing_fields else False
        param_ok = REQUIRED_PARAMS <= set(meta.get("parameters", {}))
        units_ok = REQUIRED_UNITS <= set(meta.get("units", {}))
        solver_ok = all(k in meta.get("solver_metadata", {})
                        for k in ("pipeline", "fluid_solver", "structural_solver", "mapping"))
    base.update({"missing_physics_fields": missing_fields, "field_node_shapes_consistent": bool(node_shapes),
                 "connectivity_in_bounds": bool(conn_ok), "temperature_ranges_physical": bool(temp_ok),
                 "structural_response_nonzero": response_ok, "parameter_metadata_complete": param_ok,
                 "required_units_present": units_ok, "solver_metadata_complete": solver_ok})
    base["valid"] = bool(base["valid"] and not missing_fields and node_shapes and conn_ok and temp_ok
                         and response_ok and param_ok and units_ok and solver_ok)
    return base


def validate_dataset(directory: Path, *, write_result: bool = True) -> dict:
    files = sorted(directory.glob("case_*.npz"))
    cases = [_case_checks(p) for p in files]
    parameter_sets, times = [], []
    for p in files:
        with np.load(p, allow_pickle=False) as d:
            meta = json.loads(str(d["metadata_json"]))
            parameter_sets.append(set(meta.get("parameters", {})))
            times.append(float(d["time"]) if "time" in d else None)
    checks = {"case_count_8_to_15": 8 <= len(files) <= 15,
              "all_cases_valid": bool(cases) and all(c["valid"] for c in cases),
              "parameter_schema_consistent": len({tuple(sorted(x)) for x in parameter_sets}) <= 1,
              "units_and_metadata_present": all(c["metadata_valid"] for c in cases),
              "meshes_kept_independent": all(c["independent_domain_meshes"] for c in cases),
              "no_nan_inf": all(c["all_finite"] for c in cases),
              "time_synchronization_explicit": all(t is not None for t in times),
              "field_shapes_mesh_consistent": all(c["field_node_shapes_consistent"] for c in cases),
              "interface_fields_complete": all(not c["missing_physics_fields"] for c in cases),
              "temperature_displacement_stress_ranges_valid": all(c["temperature_ranges_physical"] and c["structural_response_nonzero"] for c in cases)}
    result = {"directory": str(directory.resolve()), "case_count": len(files), "checks": checks,
              "cases": cases, "status": "PASS" if all(checks.values()) else "FAIL"}
    if write_result:
        (directory / "dataset_validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    result = validate_dataset(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/multiphysics_dataset"))
    print(result)
    raise SystemExit(0 if result["status"] == "PASS" else 1)
