"""Case D: Maxwell 2D AC magnetic skin-effect benchmark."""

from __future__ import annotations

import json
import math
import traceback

from aedt_smoke_common import (
    OUTPUT_ROOT,
    aedt_pid_set,
    aedt_processes,
    cleanup_new_aedt_processes,
    ensure_dirs,
    prepare_pyaedt_student_runtime,
    student_launch_kwargs,
    utc_now,
    write_json,
)


def _scalar_points(path):
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


def _export_complex_magnitude(app, base_quantity, solution, frequency_hz, path):
    """Bypass PyAEDT 1.4's missing EddyCurrentXY intrinsic mapping."""
    reporter = app.odesign.GetModule("FieldsReporter")
    reporter.CalcStack("clear")
    reporter.EnterQty(base_quantity)
    if base_quantity in {"J", "B"}:
        reporter.CalcOp("Smooth")
        reporter.CalcOp("CmplxMag")
    reporter.ExportOnGrid(
        str(path), ["0mm", "0mm", "0mm"], ["5mm", "0mm", "0mm"],
        ["0.5mm", "1mm", "1mm"], solution,
        ["Freq:=", f"{frequency_hz}Hz", "Phase:=", "0deg"],
        ["NAME:ExportOption", "IncludePtInOutput:=", True, "RefCSName:=", "Global", "PtInSI:=", True, "FieldInRefCS:=", True],
        "Cartesian", ["0mm", "0mm", "0mm"], False,
    )
    return str(path) if path.exists() else False


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_d_eddy_current"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "D", "name": "AC conductor skin effect", "timestamp_utc": utc_now(), "status": "FAIL"}
    baseline = aedt_pid_set()
    app = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Maxwell2d
        from ansys.aedt.core.generic.constants import SolutionsMaxwell2D

        app = Maxwell2d(project="CaseD_EddyCurrent", design="SkinEffect", solution_type=SolutionsMaxwell2D.EddyCurrentXY, **student_launch_kwargs(runtime))
        app.modeler.model_units = "mm"
        inner_r, shield_in, shield_out, depth, current, frequency = 5.0, 19.0, 20.0, 100.0, 100.0, 1000.0
        inner = app.modeler.create_circle([0, 0, 0], inner_r, name="InnerConductor", material="copper")
        shield = app.modeler.create_circle([0, 0, 0], shield_out, name="ReturnConductor", material="copper")
        hole = app.modeler.create_circle([0, 0, 0], shield_in, name="ReturnHole", material="vacuum")
        app.modeler.subtract(shield, hole, keep_originals=False)
        region = app.modeler.create_region(50, name="AirRegion")
        app.model_depth = f"{depth}mm"
        app.assign_current(inner.name, amplitude=f"{current}A", name="Current")
        app.assign_current(shield.name, amplitude=f"{current}A", swap_direction=True, name="ReturnCurrent")
        boundary = app.assign_vector_potential(region.edges, vector_value=0, boundary="VectorPotential0")
        eddy_enabled = app.eddy_effects_on([inner.name, shield.name], enable_eddy_effects=True, enable_displacement_current=False)
        app.mesh.assign_length_mesh([inner.name, shield.name], inside_selection=True, maximum_length="1.5mm", name="SkinMesh")
        setup = app.create_setup("Setup1", Frequency=f"{frequency}Hz", MaximumPasses=1, PercentError=5.0)
        solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_d_eddy_current.aedt"
        saved = bool(app.save_project(project_file))
        messages = list(app.odesktop.GetMessages(app.project_name, app.design_name, 0))
        field_exports = {}
        export_specs = (("ComplexMag_J", "J"), ("ComplexMag_B", "B"), ("OhmicLoss", "OhmicLoss"))
        for quantity, base_quantity in export_specs:
            field_file = case_dir / f"field_{quantity}.fld"
            try:
                exported = _export_complex_magnitude(app, base_quantity, f"{setup.name} : LastAdaptive", frequency, field_file)
                field_exports[quantity] = {"return": str(exported), "exists": field_file.exists(), "path": str(field_file)}
            except Exception as exc:
                field_exports[quantity] = {"error": f"{type(exc).__name__}: {exc}"}
        sigma = 5.8e7
        mu0 = 4 * math.pi * 1e-7
        skin_depth = math.sqrt(2 / (2 * math.pi * frequency * mu0 * sigma))
        j_points = _scalar_points(case_dir / "field_ComplexMag_J.fld")
        b_points = _scalar_points(case_dir / "field_ComplexMag_B.fld")
        loss_points = _scalar_points(case_dir / "field_OhmicLoss.fld")
        center_j = j_points[0][1] if j_points else None
        surface_j = j_points[-1][1] if j_points else None
        concentration = surface_j / center_j if center_j and surface_j is not None else None
        loss_positive = bool(loss_points and max(v for _, v in loss_points) > 0)
        result.update({
            "status": "PASS" if solved and saved and concentration is not None and concentration > 1.05 and loss_positive else "FAIL",
            "solver": "Maxwell 2D Eddy Current (AC Magnetic XY)", "solved": solved,
            "project_saved": saved, "project_file": str(project_file),
            "geometry": {"inner_radius_mm": inner_r, "return_inner_radius_mm": shield_in, "return_outer_radius_mm": shield_out, "depth_mm": depth},
            "excitation": {"current_A_rms_phasor": current, "return_current_A_rms_phasor": -current, "frequency_Hz": frequency},
            "boundaries": {"vector_potential": "VectorPotential0" if boundary else None, "eddy_effects_enabled": bool(eddy_enabled)},
            "solver_messages": messages,
            "results": {"J_samples_A_per_m2": j_points, "B_samples_T": b_points, "ohmic_loss_density_samples_W_per_m3": loss_points, "J_surface_to_center_ratio": concentration},
            "theory": {"copper_conductivity_S_per_m": sigma, "skin_depth_m": skin_depth, "skin_depth_mm": skin_depth * 1000, "formula": "sqrt(2/(omega*mu0*sigma))"},
            "validation": {"surface_current_concentration": concentration is not None and concentration > 1.05, "positive_ohmic_loss": loss_positive},
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
        result["cleanup"] = cleanup_new_aedt_processes(baseline)
        result["processes_after_close"] = aedt_processes()
        write_json(case_dir / "result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
