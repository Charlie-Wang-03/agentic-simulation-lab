"""Case L: ten real native-SPH dam-break parameter cases.

Each case retains its ragged Lagrangian table.  The compact X-Z projection is
an explicitly derived companion and never replaces the particle data.
"""

import json
import math
import time
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, project_xz_to_npz, read_sph_steps


OUT = OUTPUT_ROOT / "case_l_dataset"
OUT.mkdir(parents=True, exist_ok=True)
RESULT = OUT / "result.json"
INDEX = OUT / "dataset_index.json"
result = {"case": "L", "status": "FAIL", "stage": "initializing"}

try:
    specifications = []
    for height_m in (0.06, 0.08):
        for viscosity_pa_s in (0.0008, 0.0010, 0.0012, 0.0014, 0.0016):
            specifications.append((height_m, viscosity_pa_s))

    cases = []
    for number, (height_m, viscosity_pa_s) in enumerate(specifications, start=1):
        case_id = f"sph_{number:02d}_h{height_m:.2f}_mu{viscosity_pa_s:.4f}"
        case_dir = OUT / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        project = app.CreateProject()
        study = project.GetStudy()
        study.SetName(f"Case L - {case_id}")
        project_path = case_dir / f"{case_id}.rocky"
        project.SaveProject(str(project_path))
        size_m = 0.015
        configure_water_sph(
            study, size_m=size_m, solver_model="IISPH",
            viscosity_pa_s=viscosity_pa_s,
        )
        import_open_tank(study)
        add_sph_volume(
            study, name="Dam Column", center_m=(-0.115, 0.0, 0.005 + height_m / 2.0),
            dimensions_m=(0.06, 0.04, height_m), sph_size_m=size_m,
        )
        set_domain(study)
        started = time.perf_counter()
        simulation_ok = solve(study, project, project_path, duration_s=0.20, output_dt_s=0.05)
        runtime_s = time.perf_counter() - started
        table = case_dir / "sph_lagrangian.csv"
        metadata = export_lagrangian(study, table)
        projection = project_xz_to_npz(
            study, case_dir / "sph_eulerian_xz.npz",
            xlim=(-0.15, 0.15), zlim=(0.0, 0.15), shape=(31, 16),
            smoothing_length_m=2.0 * size_m,
        )
        steps, _ = read_sph_steps(study)
        masses = [sum(float(row["mass_kg"]) for row in rows) for _, rows in steps]
        mass_drift = ((max(masses) - min(masses)) / max(masses[0], 1e-30)) if masses else math.inf
        final_front = max((float(row["position_x_m"]) for row in steps[-1][1]), default=math.nan) if steps else math.nan
        cases.append({
            "case_id": case_id,
            "parameters": {"initial_height_m": height_m, "viscosity_pa_s": viscosity_pa_s, "element_size_m": size_m},
            "simulation_ok": simulation_ok,
            "runtime_s": runtime_s,
            "relative_mass_drift": mass_drift,
            "final_front_x_m": final_front,
            "particle_table": str(table),
            "particle_table_metadata": str(table.with_suffix(".metadata.json")),
            "eulerian_projection": projection,
            "project": str(project_path),
            "element_counts": metadata["element_counts"],
        })

    checks = {
        "ten_cases": len(cases) == 10,
        "all_solvers_advanced": all(case["simulation_ok"] for case in cases),
        "raw_tables_nonempty": all(max(case["element_counts"], default=0) > 0 for case in cases),
        "mass_conservation_lt_1pct": all(case["relative_mass_drift"] < 0.01 for case in cases),
        "fronts_finite": finite(case["final_front_x_m"] for case in cases),
    }
    index = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "representation": {
            "primary": "ragged_lagrangian_sph",
            "derived": "kernel_projected_eulerian_xz",
            "note": "Derived grids preserve raw particle tables as the authoritative solver output.",
        },
        "units": {"time": "s", "length": "m", "velocity": "m/s", "pressure": "Pa", "density": "kg/m3", "mass": "kg", "viscosity": "Pa.s"},
        "cases": cases,
    }
    INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")
    result.update({"status": index["status"], "checks": checks, "case_count": len(cases), "dataset_index": str(INDEX), "cases": cases})
except Exception:
    result["error"] = traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        app.Exit()
    except Exception:
        pass
