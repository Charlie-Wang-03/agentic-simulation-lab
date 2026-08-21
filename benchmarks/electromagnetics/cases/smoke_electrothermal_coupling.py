"""Case G: actual Maxwell DC-conduction loss link into an Icepak thermal design."""

from __future__ import annotations

import json
import traceback

from aedt_smoke_common import OUTPUT_ROOT, aedt_pid_set, aedt_processes, cleanup_new_aedt_processes, ensure_dirs, prepare_pyaedt_student_runtime, student_launch_kwargs, utc_now, write_json


def _scalar_values(path):
    values = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[2:]:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    values.append(float(parts[-1]))
                except ValueError:
                    pass
    return values


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_g_electrothermal"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "G", "name": "Maxwell-to-Icepak electrothermal coupling", "timestamp_utc": utc_now(), "status": "FAIL"}
    baseline = aedt_pid_set()
    maxwell = icepak = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Icepak, Maxwell3d
        from ansys.aedt.core.generic.constants import SolutionsMaxwell3D

        maxwell = Maxwell3d(project="CaseG_Electrothermal", design="BusbarDC", solution_type=SolutionsMaxwell3D.DCConduction, **student_launch_kwargs(runtime))
        maxwell.modeler.model_units = "mm"
        busbar = maxwell.modeler.create_box([0, 0, 0], [50, 10, 10], name="Busbar", material="copper")
        source = maxwell.assign_voltage([busbar.bottom_face_x.id], amplitude=1000, name="OneVolt")
        sink = maxwell.assign_voltage([busbar.top_face_x.id], amplitude=0, name="Ground")
        maxwell.mesh.assign_length_mesh([busbar.name], inside_selection=True, maximum_length="5mm", name="BusbarMesh")
        em_setup = maxwell.create_setup("EMSetup", MaximumPasses=1, PercentError=5.0)
        em_solved = bool(maxwell.analyze(setup=em_setup.name, cores=2, use_auto_settings=False))
        em_messages = list(maxwell.odesktop.GetMessages(maxwell.project_name, maxwell.design_name, 0))

        desktop = maxwell.desktop_class
        icepak = Icepak(
            project=maxwell.project_name, design="BusbarThermal", solution_type="SteadyState",
            version=runtime["discovery"]["release"], non_graphical=True, new_desktop=False,
            close_on_exit=False, student_version=True, port=desktop.port, aedt_process_id=desktop.aedt_process_id,
        )
        icepak.modeler.model_units = "mm"
        thermal_bar = icepak.modeler.create_box([0, 0, 0], [50, 10, 10], name="Busbar", material="copper")
        # The Icepak design supplies its computational region; avoid an
        # unnecessary face-ID round trip that is unreliable over 2025 R2 SV gRPC.
        opening = None
        loss_link = icepak.assign_em_losses(
            [thermal_bar.name], design="BusbarDC", setup="EMSetup", sweep="LastAdaptive",
            source_project_name=None, name="MaxwellOhmicLoss", force_source_solve=False, preserve_source_solution=True,
        )
        thermal_setup = icepak.create_setup("ThermalSetup")
        thermal_solved = bool(icepak.analyze(setup=thermal_setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_g_electrothermal.aedt"
        saved = bool(icepak.save_project(project_file))
        thermal_messages = list(icepak.odesktop.GetMessages(icepak.project_name, icepak.design_name, 0))
        temp_file = case_dir / "temperature.fld"
        temp_export = False
        temperatures = []
        if thermal_solved:
            try:
                temp_export = icepak.post.export_field_file_on_grid(
                    "Temp", solution=f"{thermal_setup.name} : SteadyState", file_name=str(temp_file),
                    grid_start=[0, 5, 5], grid_stop=[50, 5, 5], grid_step=[5, 1, 1], export_in_si_system=False,
                )
                temperatures = _scalar_values(temp_file)
            except Exception as exc:
                result["temperature_export_error"] = f"{type(exc).__name__}: {exc}"
        all_messages = em_messages + thermal_messages
        student_evidence = [m for m in all_messages if "Student" in m and ("does not support" in m or "limit" in m.lower())]
        linked = bool(loss_link)
        result.update({
            "status": "BLOCKED BY STUDENT LIMIT" if student_evidence else ("PASS" if em_solved and linked and thermal_solved and saved and temperatures else "FAIL"),
            "source_solver": "Maxwell 3D DC Conduction", "source_solved": em_solved,
            "target_solver": "Icepak SteadyState", "target_solved": thermal_solved,
            "coupling": {"method": "Icepak.AssignEMLoss", "boundary_name": "MaxwellOhmicLoss", "created": linked, "source_design": "BusbarDC", "source_solution": "EMSetup : LastAdaptive", "target_object": "Busbar"},
            "geometry": {"busbar_mm": [50, 10, 10], "material": "copper"},
            "electrical_bc": {"voltage_V": 1.0, "source_created": bool(source), "sink_created": bool(sink)},
            "thermal_bc": {"open_region_created": bool(opening), "domain": "Icepak default computational region"},
            "results": {"temperature_samples": temperatures, "min_temperature": min(temperatures) if temperatures else None, "max_temperature": max(temperatures) if temperatures else None},
            "field_exports": {"temperature": {"return": str(temp_export), "exists": temp_file.exists(), "path": str(temp_file)}},
            "project_saved": saved, "project_file": str(project_file),
            "solver_messages": {"maxwell": em_messages, "icepak": thermal_messages},
            "student_limit": {"blocked": bool(student_evidence), "evidence": student_evidence},
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    finally:
        if icepak is not None:
            try:
                icepak.release_desktop(close_projects=False, close_desktop=False)
            except Exception:
                pass
        if maxwell is not None:
            try:
                result["release_return"] = maxwell.release_desktop(close_projects=True, close_desktop=True)
            except Exception as exc:
                result["release_error"] = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = cleanup_new_aedt_processes(baseline)
        result["processes_after_close"] = aedt_processes()
        write_json(case_dir / "result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "BLOCKED BY STUDENT LIMIT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
