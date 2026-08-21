"""Case A: Maxwell 2D parallel-plate electrostatic benchmark."""

from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

from aedt_diagnostics import finalize_ladder, sanitize_evidence, static_ladder
from aedt_smoke_common import (
    OUTPUT_ROOT,
    aedt_pid_set,
    aedt_processes,
    cleanup_new_aedt_processes,
    collect_phase0,
    ensure_dirs,
    prepare_pyaedt_student_runtime,
    student_launch_kwargs,
    utc_now,
    write_json,
)


class SupportedPathBlocked(RuntimeError):
    """Raised when static evidence proves the authorized transport unavailable."""


def _parse_capacitance(path: Path, depth_m: float) -> tuple[float | None, float | None, str]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    match = re.search(
        r"^\s*Signal\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    value = float(match.group(1)) if match else None
    unit_match = re.search(r"Capacitance Unit:\s*(\w+)", text, re.IGNORECASE)
    scale = {"f": 1.0, "nf": 1e-9, "pf": 1e-12}.get(unit_match.group(1).casefold(), 1.0) if unit_match else 1.0
    per_meter = value * scale if value is not None else None
    return (per_meter * depth_m if per_meter is not None else None), per_meter, text


def _parse_scalar_field(path: Path) -> list[float]:
    values = []
    if not path.exists():
        return values
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
    case_dir = OUTPUT_ROOT / "case_a_electrostatic"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "A", "name": "Parallel-plate electrostatic", "timestamp_utc": utc_now(), "status": "FAIL"}
    baseline = aedt_pid_set()
    app = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        phase0 = collect_phase0()
        from ansys.aedt.core.generic.settings import settings

        secure_local = bool(settings.grpc_secure_mode and settings.grpc_local)
        ladder = static_ladder(
            python_version=phase0["host"]["python_version"],
            pyaedt_version=phase0["pyaedt"]["version"],
            module_available=phase0["pyaedt"]["module_available"],
            discovery=runtime["discovery"],
            secure_local=secure_local,
        )
        result["diagnosis_ladder"] = ladder
        if ladder["phases"]["version_compatibility"]["status"] == "BLOCKED":
            raise SupportedPathBlocked(ladder["phases"]["version_compatibility"]["reason"])
        from ansys.aedt.core import Maxwell2d
        from ansys.aedt.core.modules.boundary.maxwell_boundary import MatrixElectric

        app = Maxwell2d(
            project="CaseA_Electrostatic",
            design="ParallelPlate2D",
            solution_type="Electrostatic",
            **student_launch_kwargs(runtime),
        )
        ladder["phases"]["session_startup"] = {"status": "PASS", "constructor": "Maxwell2d"}
        ladder["phases"]["project_design_creation"] = {"status": "PASS"}
        app.modeler.model_units = "mm"
        width_mm, gap_mm, thickness_mm, voltage = 100.0, 10.0, 1.0, 1.0
        lower = app.modeler.create_rectangle(
            [-width_mm / 2, -gap_mm / 2 - thickness_mm, 0],
            [width_mm, thickness_mm],
            name="LowerPlate",
            material="copper",
        )
        upper = app.modeler.create_rectangle(
            [-width_mm / 2, gap_mm / 2, 0],
            [width_mm, thickness_mm],
            name="UpperPlate",
            material="copper",
        )
        region = app.modeler.create_region([100, 500, 100, 100], name="AirRegion")
        app.model_depth = "100mm"
        ground = app.assign_voltage([lower.name], amplitude="0V", name="Ground")
        signal = app.assign_voltage([upper.name], amplitude="1V", name="Signal")
        balloon = app.assign_balloon(region.edges, boundary="OuterBoundary")
        matrix = app.assign_matrix(MatrixElectric(signal_sources=[signal.name], ground_sources=[ground.name], matrix_name="CapMatrix"))
        app.mesh.assign_length_mesh([upper.name, lower.name], inside_selection=True, maximum_length="2mm", name="PlateMesh")
        setup = app.create_setup("Setup1", MaximumPasses=5, PercentError=0.5)
        solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_a_electrostatic.aedt"
        saved = bool(app.save_project(project_file))
        matrix_file = case_dir / "capacitance_matrix.txt"
        matrix_exported = bool(app.export_matrix(matrix.name, matrix_file, setup=setup.name)) if solved else False
        depth_m = 0.1
        capacitance, capacitance_per_m, matrix_text = _parse_capacitance(matrix_file, depth_m)
        solution = f"{setup.name} : LastAdaptive"
        field_exports = {}
        for quantity, is_vector in (("Voltage", False), ("Mag_E", False), ("E", True)):
            field_file = case_dir / f"field_{quantity}.fld"
            try:
                exported = app.post.export_field_file_on_grid(
                    quantity,
                    solution=solution,
                    file_name=str(field_file),
                    grid_start=[-40, -4, 0],
                    grid_stop=[40, 4, 0],
                    grid_step=[10, 1, 1],
                    is_vector=is_vector,
                    export_in_si_system=True,
                )
                field_exports[quantity] = {"return": str(exported), "exists": field_file.exists(), "path": str(field_file)}
            except Exception as exc:  # noqa: BLE001 - individual field export is supporting solver evidence
                field_exports[quantity] = {"error": f"{type(exc).__name__}: {exc}"}
        epsilon0 = 8.8541878128e-12
        area_m2 = width_mm / 1000 * 0.1
        gap_m = gap_mm / 1000
        c_theory = epsilon0 * area_m2 / gap_m
        e_theory = voltage / gap_m
        energy_theory = 0.5 * c_theory * voltage**2
        rel_error = abs(capacitance - c_theory) / c_theory if capacitance is not None else None
        e_values = _parse_scalar_field(case_dir / "field_Mag_E.fld")
        e_mean = sum(e_values) / len(e_values) if e_values else None
        e_rel_error = abs(e_mean - e_theory) / e_theory if e_mean is not None else None
        result.update(
            {
                "status": "PASS" if solved and saved and capacitance is not None and rel_error < 0.25 and e_rel_error is not None and e_rel_error < 0.05 else "FAIL",
                "solver": "Maxwell 2D Electrostatic",
                "solved": solved,
                "project_saved": saved,
                "project_file": str(project_file),
                "geometry": {"plate_width_mm": width_mm, "model_depth_mm": 100.0, "gap_mm": gap_mm, "plate_thickness_mm": thickness_mm},
                "excitation": {"voltage_V": voltage},
                "boundaries": {"ground": ground.name, "signal": signal.name, "balloon": getattr(balloon, "name", str(balloon))},
                "matrix": {"name": matrix.name, "exported": matrix_exported, "path": str(matrix_file), "raw": matrix_text, "capacitance_per_meter_F_per_m": capacitance_per_m, "depth_scaling_m": depth_m},
                "results": {"capacitance_F": capacitance, "electric_field_mean_V_per_m": e_mean, "stored_energy_from_capacitance_J": 0.5 * capacitance * voltage**2 if capacitance else None},
                "theory": {"capacitance_F": c_theory, "electric_field_V_per_m": e_theory, "stored_energy_J": energy_theory},
                "relative_error": {"capacitance": rel_error, "electric_field": e_rel_error},
                "field_exports": field_exports,
            }
        )
        ladder["phases"]["minimal_solve"] = {
            "status": "PASS" if result["status"] == "PASS" else "FAIL",
            "solver_completed": solved,
            "physics_checks_passed": result["status"] == "PASS",
        }
    except SupportedPathBlocked as exc:
        result["status"] = "BLOCKED"
        result["error"] = f"SupportedPathBlocked: {exc}"
    except Exception as exc:  # noqa: BLE001 - solver/API failures must become durable evidence
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
        ladder = result.get("diagnosis_ladder")
        if ladder and ladder["phases"]["session_startup"]["status"] == "NOT_RUN":
            ladder["phases"]["session_startup"] = {
                "status": "FAIL",
                "exception_type": type(exc).__name__,
                "message": str(exc),
            }
    finally:
        if app is not None:
            try:
                result["release_return"] = app.release_desktop(close_projects=True, close_desktop=True)
            except Exception as exc:  # noqa: BLE001 - cleanup failures must become durable evidence
                result["release_error"] = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = cleanup_new_aedt_processes(baseline)
        result["processes_after_close"] = aedt_processes()
        ladder = result.get("diagnosis_ladder")
        if ladder:
            remaining = [pid for item in result["cleanup"] for pid in item["remaining"]]
            ladder["phases"]["release_cleanup"] = {
                "status": "PASS" if not remaining else "FAIL",
                "remaining_owned_process_count": len(remaining),
            }
            result["diagnosis_ladder"] = finalize_ladder(ladder["phases"])
            result["public_diagnosis"] = sanitize_evidence(result["diagnosis_ladder"])
        write_json(case_dir / "result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "BLOCKED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
