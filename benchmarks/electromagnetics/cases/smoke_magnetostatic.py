"""Case C: Maxwell 2D coaxial current/return magnetostatic benchmark."""

from __future__ import annotations

import json
import math
import re
import traceback
from pathlib import Path

from aedt_smoke_common import OUTPUT_ROOT, aedt_pid_set, aedt_processes, cleanup_new_aedt_processes, ensure_dirs, prepare_pyaedt_student_runtime, student_launch_kwargs, utc_now, write_json


def _matrix_value(path: Path, row_name: str) -> tuple[float | None, str | None, str]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    unit_match = re.search(r"Inductance Unit:\s*(\w+)", text, re.I)
    match = re.search(rf"^\s*{re.escape(row_name)}\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*$", text, re.I | re.M)
    return (float(match.group(1)) if match else None), (unit_match.group(1) if unit_match else None), text


def _scalar_points(path: Path) -> list[tuple[float, float]]:
    points = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[2:]:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    points.append((float(parts[0]), float(parts[-1])))
                except ValueError:
                    pass
    return points


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_c_magnetostatic"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "C", "name": "Coaxial current-return magnetostatic", "timestamp_utc": utc_now(), "status": "FAIL"}
    baseline = aedt_pid_set()
    app = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Maxwell2d
        from ansys.aedt.core.generic.constants import SolutionsMaxwell2D

        app = Maxwell2d(project="CaseC_Magnetostatic", design="CoaxialMagneticField", solution_type=SolutionsMaxwell2D.MagnetostaticXY, **student_launch_kwargs(runtime))
        app.modeler.model_units = "mm"
        inner_r_mm, return_inner_r_mm, return_outer_r_mm, depth_mm, current_a = 5.0, 19.0, 20.0, 100.0, 100.0
        inner = app.modeler.create_circle([0, 0, 0], inner_r_mm, name="InnerConductor", material="copper")
        outer = app.modeler.create_circle([0, 0, 0], return_outer_r_mm, name="ReturnConductor", material="copper")
        hole = app.modeler.create_circle([0, 0, 0], return_inner_r_mm, name="ReturnHole", material="vacuum")
        app.modeler.subtract(outer, hole, keep_originals=False)
        # Keep the initial/adaptive mesh below the AEDT Student 2-D element cap.
        # A 50% padding still leaves the zero-potential boundary one outer-radius
        # away from the coax shield, whose net enclosed current is zero.
        region = app.modeler.create_region(50, name="AirRegion")
        app.model_depth = f"{depth_mm}mm"
        source = app.assign_current(inner.name, amplitude=f"{current_a}A", name="Current")
        return_source = app.assign_current(outer.name, amplitude=f"{current_a}A", swap_direction=True, name="ReturnCurrent")
        outer_boundary = app.assign_vector_potential(region.edges, vector_value=0, boundary="VectorPotential0")
        app.mesh.assign_length_mesh([inner.name, outer.name], inside_selection=True, maximum_length="3mm", name="ConductorMesh")
        setup = app.create_setup("Setup1", MaximumPasses=1, PercentError=5.0)
        solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_c_magnetostatic.aedt"
        saved = bool(app.save_project(project_file))
        messages = list(app.odesktop.GetMessages(app.project_name, app.design_name, 0))
        energy_per_m = None
        if solved:
            try:
                energy_per_m = float(app.post.get_scalar_field_value("Energy", "Integrate", solution=f"{setup.name} : LastAdaptive"))
            except Exception:
                energy_per_m = None
        inductance_per_m = 2 * energy_per_m / current_a**2 if energy_per_m else None
        inductance = inductance_per_m * depth_mm / 1000 if inductance_per_m is not None else None
        field_exports = {}
        for quantity in ("Mag_B", "Mag_H", "B", "H"):
            field_file = case_dir / f"field_{quantity}.fld"
            try:
                exported = app.post.export_field_file_on_grid(
                    quantity, solution=f"{setup.name} : LastAdaptive", file_name=str(field_file),
                    grid_start=[6, 0, 0], grid_stop=[18, 0, 0], grid_step=[2, 1, 1],
                    is_vector=quantity in {"B", "H"}, export_in_si_system=True,
                )
                field_exports[quantity] = {"return": str(exported), "exists": field_file.exists(), "path": str(field_file)}
            except Exception as exc:
                field_exports[quantity] = {"error": f"{type(exc).__name__}: {exc}"}
        mu0 = 4 * math.pi * 1e-7
        b_points = _scalar_points(case_dir / "field_Mag_B.fld")
        h_points = _scalar_points(case_dir / "field_Mag_H.fld")
        b_errors = [abs(value - mu0 * current_a / (2 * math.pi * abs(x))) / (mu0 * current_a / (2 * math.pi * abs(x))) for x, value in b_points if x]
        h_errors = [abs(value - current_a / (2 * math.pi * abs(x))) / (current_a / (2 * math.pi * abs(x))) for x, value in h_points if x]
        l_per_m_theory = mu0 / (2 * math.pi) * math.log((return_inner_r_mm / 1000) / (inner_r_mm / 1000))
        l_theory = l_per_m_theory * depth_mm / 1000
        l_error = abs(inductance - l_theory) / l_theory if inductance is not None else None
        b_mean_error = sum(b_errors) / len(b_errors) if b_errors else None
        h_mean_error = sum(h_errors) / len(h_errors) if h_errors else None
        result.update({
            "status": "PASS" if solved and saved and l_error is not None and l_error < 0.25 and b_mean_error is not None and b_mean_error < 0.1 and h_mean_error is not None and h_mean_error < 0.1 else "FAIL",
            "solver": "Maxwell 2D Magnetostatic", "solved": solved, "project_saved": saved, "project_file": str(project_file),
            "geometry": {"inner_radius_mm": inner_r_mm, "return_inner_radius_mm": return_inner_r_mm, "return_outer_radius_mm": return_outer_r_mm, "depth_mm": depth_mm},
            "excitation": {"current_A": current_a, "return_current_A": -current_a}, "boundaries": {"vector_potential": "VectorPotential0"},
            "solver_messages": messages,
            "matrix": {"method": "2*integrated_field_energy/I^2", "energy_per_m_J_per_m": energy_per_m, "inductance_per_m_H_per_m": inductance_per_m},
            "results": {"inductance_H": inductance, "flux_linkage_Wb_turn": inductance * current_a if inductance else None, "magnetic_energy_J": 0.5 * inductance * current_a**2 if inductance else None, "B_samples": b_points, "H_samples": h_points},
            "theory": {"inductance_per_m_H_per_m": l_per_m_theory, "inductance_H": l_theory, "flux_linkage_Wb_turn": l_theory * current_a, "magnetic_energy_J": 0.5 * l_theory * current_a**2, "B_formula": "mu0*I/(2*pi*r)", "H_formula": "I/(2*pi*r)"},
            "relative_error": {"inductance": l_error, "B_mean": b_mean_error, "H_mean": h_mean_error}, "field_exports": field_exports,
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    finally:
        if app is not None:
            try:
                result["release_return"] = app.release_desktop(close_projects=True, close_desktop=True)
            except Exception as exc:
                result["release_error"] = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = cleanup_new_aedt_processes(baseline)
        result["processes_after_close"] = aedt_processes()
        write_json(case_dir / "result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
