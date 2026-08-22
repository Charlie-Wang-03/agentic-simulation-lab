"""Case B: Maxwell 2D uniform DC conductor benchmark."""

from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

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


def _matrix_value(path: Path, row_name: str) -> tuple[float | None, str | None, str]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    unit_match = re.search(r"(?:Conductance|Resistance) Unit:\s*(\w+)", text, re.I)
    match = re.search(rf"^\s*{re.escape(row_name)}\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*$", text, re.I | re.M)
    return (float(match.group(1)) if match else None), (unit_match.group(1) if unit_match else None), text


def _scalar_mean(path: Path) -> float | None:
    values = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[2:]:
            parts = line.split()
            try:
                values.append(float(parts[-1]))
            except (IndexError, ValueError):
                pass
    return sum(values) / len(values) if values else None


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_b_dc_conduction"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "B", "name": "Uniform DC conductor", "timestamp_utc": utc_now(), "status": "FAIL"}
    app = None
    owned_pid = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Maxwell2d
        from ansys.aedt.core.modules.boundary.maxwell_boundary import MatrixElectric

        app = Maxwell2d(project="CaseB_DCConduction", design="UniformResistor2D", solution_type="DCConduction", **student_launch_kwargs(runtime))
        owned_pid = getattr(app.desktop_class, "aedt_process_id", None)
        app.modeler.model_units = "mm"
        sigma, length_mm, width_mm, depth_mm, voltage = 5.8e7, 100.0, 10.0, 10.0, 1.0
        copper = app.materials.add_material("BenchmarkCopper")
        copper.conductivity = sigma
        conductor = app.modeler.create_rectangle([0, 0, 0], [length_mm, width_mm], name="Conductor", material=copper.name)
        app.model_depth = f"{depth_mm}mm"
        left_edge = app.modeler.get_edgeid_from_position([0, width_mm / 2, 0], assignment=conductor.name)
        right_edge = app.modeler.get_edgeid_from_position([length_mm, width_mm / 2, 0], assignment=conductor.name)
        ground = app.assign_voltage([left_edge], amplitude="0V", name="Ground")
        signal = app.assign_voltage([right_edge], amplitude="1V", name="Signal")
        matrix = app.assign_matrix(MatrixElectric(signal_sources=[signal.name], ground_sources=[ground.name], matrix_name="ConductanceMatrix"))
        app.mesh.assign_length_mesh([conductor.name], inside_selection=True, maximum_length="2mm", name="ConductorMesh")
        setup = app.create_setup("Setup1", MaximumPasses=4, PercentError=0.5)
        solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_b_dc_conduction.aedt"
        saved = bool(app.save_project(project_file))
        matrix_file = case_dir / "conductance_matrix.txt"
        matrix_exported = bool(app.export_matrix(matrix.name, matrix_file, setup=setup.name)) if solved else False
        raw_value, raw_unit, matrix_text = _matrix_value(matrix_file, signal.name)
        scale = {"s": 1.0, "sie": 1.0, "ms": 1e-3, "msie": 1e-3, "us": 1e-6, "usie": 1e-6}.get((raw_unit or "S").casefold(), 1.0)
        conductance_per_m = raw_value * scale if raw_value is not None else None
        conductance = conductance_per_m * (depth_mm / 1000) if conductance_per_m is not None else None
        resistance = 1 / conductance if conductance else None
        field_exports = {}
        for quantity in ("Mag_E", "Mag_J", "J", "OhmicLoss"):
            field_file = case_dir / f"field_{quantity}.fld"
            try:
                exported = app.post.export_field_file_on_grid(
                    quantity,
                    solution=f"{setup.name} : LastAdaptive",
                    file_name=str(field_file),
                    grid_start=[5, 1, 0], grid_stop=[95, 9, 0], grid_step=[10, 2, 1],
                    is_vector=quantity == "J", export_in_si_system=True,
                )
                field_exports[quantity] = {"return": str(exported), "exists": field_file.exists(), "path": str(field_file)}
            except Exception as exc:
                field_exports[quantity] = {"error": f"{type(exc).__name__}: {exc}"}
        area_m2 = width_mm / 1000 * depth_mm / 1000
        length_m = length_mm / 1000
        resistance_theory = length_m / (sigma * area_m2)
        current_theory = voltage / resistance_theory
        e_theory = voltage / length_m
        j_theory = current_theory / area_m2
        power_theory = voltage * current_theory
        e_mean = _scalar_mean(case_dir / "field_Mag_E.fld")
        j_mean = _scalar_mean(case_dir / "field_Mag_J.fld")
        errors = {
            "resistance": abs(resistance - resistance_theory) / resistance_theory if resistance is not None else None,
            "electric_field": abs(e_mean - e_theory) / e_theory if e_mean is not None else None,
            "current_density": abs(j_mean - j_theory) / j_theory if j_mean is not None else None,
        }
        result.update({
            "status": "PASS" if solved and saved and all(value is not None and value < 0.05 for value in errors.values()) else "FAIL",
            "solver": "Maxwell 2D DC Conduction", "solved": solved, "project_saved": saved, "project_file": str(project_file),
            "geometry": {"length_mm": length_mm, "width_mm": width_mm, "depth_mm": depth_mm},
            "material": {"conductivity_S_per_m": sigma}, "excitation": {"voltage_V": voltage},
            "matrix": {"exported": matrix_exported, "raw_value": raw_value, "raw_unit": raw_unit, "conductance_per_m_S_per_m": conductance_per_m, "text": matrix_text},
            "results": {"conductance_S": conductance, "resistance_ohm": resistance, "current_A": voltage * conductance if conductance else None, "electric_field_mean_V_per_m": e_mean, "current_density_mean_A_per_m2": j_mean, "joule_power_W": voltage**2 * conductance if conductance else None},
            "theory": {"resistance_ohm": resistance_theory, "current_A": current_theory, "electric_field_V_per_m": e_theory, "current_density_A_per_m2": j_theory, "joule_power_W": power_theory},
            "relative_error": errors, "field_exports": field_exports,
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
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
