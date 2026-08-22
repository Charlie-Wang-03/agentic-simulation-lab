"""Case F: HFSS WR-90 rectangular waveguide TE10 benchmark."""

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


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_f_hfss_waveguide"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "F", "name": "HFSS rectangular waveguide TE10", "timestamp_utc": utc_now(), "status": "FAIL"}
    app = None
    owned_pid = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Hfss

        app = Hfss(
            project="CaseF_HFSS_Waveguide",
            design="WR90_TE10",
            solution_type="Modal",
            **student_launch_kwargs(runtime),
        )
        owned_pid = getattr(app.desktop_class, "aedt_process_id", None)
        app.modeler.model_units = "mm"
        a_mm, b_mm, length_mm = 22.86, 10.16, 50.0
        waveguide = app.modeler.create_box(
            [-a_mm / 2, -b_mm / 2, 0], [a_mm, b_mm, length_mm], name="WaveguideVacuum", material="vacuum"
        )
        p1_face = app.modeler.get_faceid_from_position([0, 0, 0], assignment=waveguide.name)
        p2_face = app.modeler.get_faceid_from_position([0, 0, length_mm], assignment=waveguide.name)
        wall_faces = [face.id for face in waveguide.faces if face.id not in {p1_face, p2_face}]
        walls = app.assign_perfect_e(wall_faces, name="PEC_Walls")
        p1 = app.wave_port(
            p1_face,
            integration_line=[[0, -b_mm / 2, 0], [0, b_mm / 2, 0]],
            name="P1",
            renormalize=False,
        )
        p2 = app.wave_port(
            p2_face,
            integration_line=[[0, -b_mm / 2, length_mm], [0, b_mm / 2, length_mm]],
            name="P2",
            renormalize=False,
        )
        setup = app.create_setup(
            "Setup1", setup_type="HFSSDriven", Frequency="10GHz", MaximumPasses=5, MaxDeltaS=0.02, MinimumPasses=2
        )
        sweep = setup.create_frequency_sweep(
            unit="GHz",
            name="Sweep1",
            start_frequency=6.0,
            stop_frequency=12.0,
            num_of_freq_points=13,
            sweep_type="Discrete",
            save_fields=True,
        )
        solved = bool(app.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        project_file = case_dir / "case_f_hfss_waveguide.aedt"
        saved = bool(app.save_project(project_file))
        expressions = ["dB(S(P1,P1))", "dB(S(P2,P1))"]
        frequencies = []
        s11_db = []
        s21_db = []
        if solved:
            data = app.post.get_solution_data(
                expressions=expressions,
                setup_sweep_name=f"{setup.name} : {sweep.name}",
                primary_sweep_variable="Freq",
            )
            if data:
                freq_values, s11_values = data.get_expression_data(expressions[0], formula="real", convert_to_SI=True)
                _, s21_values = data.get_expression_data(expressions[1], formula="real", convert_to_SI=True)
                frequencies = [float(value) for value in freq_values]
                s11_db = [float(value) for value in s11_values]
                s21_db = [float(value) for value in s21_values]
        field_exports = {}
        for quantity, is_vector in (("Mag_E", False), ("E", True), ("H", True)):
            field_file = case_dir / f"field_{quantity}_10GHz.fld"
            try:
                exported = app.post.export_field_file_on_grid(
                    quantity,
                    solution=f"{setup.name} : LastAdaptive",
                    variations=app.available_variations.nominal_values,
                    file_name=str(field_file),
                    grid_start=[-10, -4, 25],
                    grid_stop=[10, 4, 25],
                    grid_step=[2, 2, 1],
                    is_vector=is_vector,
                    intrinsics={"Freq": "10GHz", "Phase": "0deg"},
                    export_in_si_system=True,
                )
                field_exports[quantity] = {"return": str(exported), "exists": field_file.exists(), "path": str(field_file)}
            except Exception as exc:
                field_exports[quantity] = {"error": f"{type(exc).__name__}: {exc}"}
        c0 = 299_792_458.0
        fc_hz = c0 / (2 * a_mm / 1000)
        above_cutoff = [(f, s) for f, s in zip(frequencies, s21_db) if f > fc_hz]
        below_cutoff = [(f, s) for f, s in zip(frequencies, s21_db) if f < fc_hz]
        passband_s21_max = max((s for _, s in above_cutoff), default=None)
        below_cutoff_s21_max = max((s for _, s in below_cutoff), default=None)
        trend_ok = (
            passband_s21_max is not None
            and passband_s21_max > -1.5
            and (below_cutoff_s21_max is None or below_cutoff_s21_max < passband_s21_max - 3)
        )
        result.update(
            {
                "status": "PASS" if solved and saved and len(frequencies) == 13 and trend_ok else "FAIL",
                "solver": "HFSS Driven Modal",
                "solved": solved,
                "project_saved": saved,
                "project_file": str(project_file),
                "geometry": {"a_mm": a_mm, "b_mm": b_mm, "length_mm": length_mm, "standard": "WR-90"},
                "boundaries": {"walls": walls.name, "port_1": p1.name, "port_2": p2.name},
                "solution_type": app.solution_type,
                "theory": {"te10_cutoff_Hz": fc_hz, "te10_cutoff_GHz": fc_hz / 1e9},
                "s_parameters": {"frequency_Hz": frequencies, "s11_dB": s11_db, "s21_dB": s21_db},
                "checks": {"point_count": len(frequencies), "passband_s21_max_dB": passband_s21_max, "below_cutoff_s21_max_dB": below_cutoff_s21_max, "cutoff_trend_ok": trend_ok},
                "field_exports": field_exports,
            }
        )
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
