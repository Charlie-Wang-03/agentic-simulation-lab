"""Case E: Maxwell 2D transient, time-varying current and electromagnetic force."""

from __future__ import annotations

import json
import math
import traceback

from aedt_smoke_common import (
    OUTPUT_ROOT,
    aedt_processes,
    cleanup_owned_process,
    ensure_dirs,
    prepare_pyaedt_student_runtime,
    student_launch_kwargs,
    utc_now,
    write_json,
)


def _scalar_points(path):
    values = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[2:]:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    values.append((float(parts[0]), float(parts[-1])))
                except ValueError:
                    pass
    return values


def _export_b_at_time(app, solution, time_value, path):
    reporter = app.odesign.GetModule("FieldsReporter")
    reporter.CalcStack("clear")
    reporter.EnterQty("B")
    reporter.CalcOp("Smooth")
    reporter.CalcOp("Mag")
    reporter.ExportOnGrid(
        str(path), ["8mm", "0mm", "0mm"], ["18mm", "0mm", "0mm"],
        ["2mm", "1mm", "1mm"], solution, ["Time:=", time_value],
        ["NAME:ExportOption", "IncludePtInOutput:=", True, "RefCSName:=", "Global", "PtInSI:=", True, "FieldInRefCS:=", True],
        "Cartesian", ["0mm", "0mm", "0mm"], False,
    )
    return str(path) if path.exists() else False


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_e_transient"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "E", "name": "Transient eccentric current-return force", "timestamp_utc": utc_now(), "status": "FAIL"}
    app = None
    owned_pid = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Maxwell2d
        from ansys.aedt.core.generic.constants import SolutionsMaxwell2D

        app = Maxwell2d(project="CaseE_Transient", design="TransientForce", solution_type=SolutionsMaxwell2D.TransientXY, **student_launch_kwargs(runtime))
        owned_pid = getattr(app.desktop_class, "aedt_process_id", None)
        app.modeler.model_units = "mm"
        inner_r, eccentricity, shield_in, shield_out, depth, peak_current = 5.0, 2.0, 19.0, 20.0, 100.0, 100.0
        inner = app.modeler.create_circle([eccentricity, 0, 0], inner_r, name="MovingConductor", material="copper")
        shield = app.modeler.create_circle([0, 0, 0], shield_out, name="ReturnConductor", material="copper")
        hole = app.modeler.create_circle([0, 0, 0], shield_in, name="ReturnHole", material="vacuum")
        app.modeler.subtract(shield, hole, keep_originals=False)
        region = app.modeler.create_region(50, name="AirRegion")
        app.model_depth = f"{depth}mm"
        current_expression = f"{peak_current}A*sin(2*pi*50Hz*Time)"
        app.assign_current(inner.name, amplitude=current_expression, name="DriveCurrent")
        app.assign_current(shield.name, amplitude=current_expression, swap_direction=True, name="ReturnCurrent")
        app.assign_vector_potential(region.edges, vector_value=0, boundary="VectorPotential0")
        app.eddy_effects_on([inner.name, shield.name], enable_eddy_effects=True, enable_displacement_current=False)
        force = app.assign_force([inner.name], force_name="ConductorForce")
        app.mesh.assign_length_mesh([inner.name, shield.name], inside_selection=True, maximum_length="2mm", name="TransientMesh")
        setup = app.create_setup("Setup1", StopTime="10ms", TimeStep="1ms")
        setup.set_save_fields(enable=True, range_type="Custom", subrange_type="LinearStep", start=0, stop=10, count=1, units="ms")
        solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_e_transient.aedt"
        saved = bool(app.save_project(project_file))
        messages = list(app.odesktop.GetMessages(app.project_name, app.design_name, 0))
        sweeps = list(app.existing_analysis_sweeps)
        solution = next((s for s in sweeps if s.startswith("Setup1")), "Setup1 : Transient")

        force_data = {"expressions_attempted": ["ConductorForce.Force_x", "ConductorForce.Force_y"], "samples": []}
        quantities = []
        try:
            quantities = list(app.post.available_report_quantities(solution=solution))
            force_exprs = [q for q in quantities if "ConductorForce" in q and "Force" in q]
            if not force_exprs:
                force_exprs = ["ConductorForce.Force_x", "ConductorForce.Force_y"]
            data = app.post.get_solution_data(expressions=force_exprs, setup_sweep_name=solution, domain="Time", primary_sweep_variable="Time")
            if data:
                times = [float(v) for v in data.primary_sweep_values]
                for idx, time_s in enumerate(times):
                    row = {"time_s": time_s}
                    for expr in force_exprs:
                        _, vals = data.get_expression_data(expression=expr, formula="real", convert_to_SI=True)
                        if idx < len(vals):
                            row[expr] = float(vals[idx])
                    force_data["samples"].append(row)
                force_data["expressions"] = force_exprs
                force_data["units"] = {expr: data.units_data.get(expr) for expr in force_exprs}
        except Exception as exc:
            force_data["error"] = f"{type(exc).__name__}: {exc}"

        time_values = ["0ms", "2ms", "5ms", "8ms", "10ms"]
        b_time_series = []
        field_exports = {}
        for time_value in time_values:
            path = case_dir / f"field_Mag_B_{time_value}.fld"
            try:
                exported = _export_b_at_time(app, solution, time_value, path)
                pts = _scalar_points(path)
                max_b = max((v for _, v in pts), default=None)
                b_time_series.append({"time": time_value, "max_B_T": max_b, "samples": pts})
                field_exports[time_value] = {"return": str(exported), "exists": path.exists(), "path": str(path)}
            except Exception as exc:
                field_exports[time_value] = {"error": f"{type(exc).__name__}: {exc}"}
        nonzero_b = [x["max_B_T"] for x in b_time_series if x["max_B_T"] is not None and x["max_B_T"] > 0]
        force_rows = [row for row in force_data.get("samples", []) if len(row) > 1]
        student_blocked = any("Student does not support Maxwell Transient" in message for message in messages)
        result.update({
            "status": "BLOCKED BY STUDENT LIMIT" if student_blocked else ("PASS" if solved and saved and len(nonzero_b) >= 2 and force_rows else "FAIL"),
            "solver": "Maxwell 2D Transient XY", "solved": solved, "project_saved": saved,
            "project_file": str(project_file), "solution": solution, "available_sweeps": sweeps,
            "geometry": {"inner_radius_mm": inner_r, "eccentricity_mm": eccentricity, "return_inner_radius_mm": shield_in, "return_outer_radius_mm": shield_out, "depth_mm": depth},
            "excitation": {"expression": current_expression, "peak_current_A": peak_current, "frequency_Hz": 50.0},
            "boundaries": {"vector_potential": "VectorPotential0", "force_parameter": "ConductorForce" if force else None},
            "setup": {"stop_time": "10ms", "time_step": "1ms", "saved_field_times": time_values},
            "solver_messages": messages, "force_time_response": force_data,
            "B_time_response": b_time_series, "available_report_quantities": quantities,
            "validation": {"multiple_nonzero_B_states": len(nonzero_b) >= 2, "force_time_series_present": bool(force_rows)},
            "student_limit": {"blocked": student_blocked, "evidence": [m for m in messages if "Student does not support" in m]},
            "field_exports": field_exports,
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
        result["cleanup"] = cleanup_owned_process(owned_pid)
        result["processes_after_close"] = aedt_processes()
        write_json(case_dir / "result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "BLOCKED BY STUDENT LIMIT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
