"""Case D: shortened official oscillating-plate two-way transient FSI."""

from __future__ import annotations

import csv
import re
import sys

import numpy as np

from fluent_smoke_common import fluent_session
from fluent_smoke_common import read_fluent_ascii_export
from multiphysics_common import OUT, mapdl_session, multiphysics_processes, system_coupling_session, wait_for_process_cleanup, write_json


CASE = "fsi_two_way"
ASSET = OUT / "official_assets" / "oscillating_plate.cas.h5"


def postprocess_existing() -> int:
    """Finalize an already completed coupling run after a post-query failure."""
    from ansys.mapdl import reader as mapdl_reader

    run_dir = OUT / CASE
    syc_dir = run_dir / "system-coupling" / "SyC"
    interface_csv = syc_dir / "Interface-1.csv"
    with interface_csv.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    last_by_step = {}
    for row in rows:
        last_by_step[int(row["Step"])] = row
    history = []
    for step, row in sorted(last_by_step.items()):
        history.append({
            "step": step, "time_s": float(row["Time"]),
            "interface_displacement_x_m": float(row["displacement (Weighted Average): Solid x"]),
            "fluid_force_x_N": float(row["Force (Sum): Fluid x"]),
            "fluid_force_y_N": float(row["Force (Sum): Fluid y"]),
        })
    for index, row in enumerate(history):
        row["interface_velocity_x_m_s"] = 0.0 if index == 0 else (
            row["interface_displacement_x_m"] - history[index-1]["interface_displacement_x_m"]
        ) / (row["time_s"] - history[index-1]["time_s"])
    final = last_by_step[max(last_by_step)]
    fluid_force = np.asarray([float(final[f"Force (Sum): Fluid {axis}"]) for axis in "xyz"])
    solid_force = np.asarray([float(final[f"Force (Sum): Solid {axis}"]) for axis in "xyz"])
    force_error = float(np.linalg.norm(fluid_force-solid_force)/max(np.linalg.norm(fluid_force), 1e-30))
    result = mapdl_reader.read_binary(run_dir / "mapdl" / "file.rst")
    _node_ids, final_disp = result.nodal_displacement(result.nsets-1)
    max_tip = float(np.max(np.linalg.norm(final_disp, axis=1)))
    try:
        _stress_ids, stress = result.nodal_stress(result.nsets-1)
        sx, sy, sz, sxy, syz, sxz = stress.T
        von_mises = np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(sxy**2+syz**2+sxz**2))
        max_stress = float(np.nanmax(von_mises))
    except Exception:
        max_stress = None
    final_case = run_dir / "fluent" / "oscillating_plate-1-00010.cas.h5"
    raw = run_dir / "fluent" / "fsi_two_way_final_field.csv"
    with fluent_session(dimension=3, processor_count=1, cwd=run_dir / "fluent", start_transcript=False) as fluent:
        fluent.settings.file.read_case_data(file_name=str(final_case))
        fluent.settings.file.export.ascii(
            file_name=str(raw), surface_name_list=["symmetry1", "wall_deforming"], delimiter="comma",
            quantities=["x-coordinate", "y-coordinate", "z-coordinate", "pressure", "x-velocity", "y-velocity", "z-velocity", "velocity-magnitude"], location="node"
        )
        volumes = fluent.settings.results.report.volume_integrals
        min_volume_result = volumes.get_minimum(cell_zones=["part-fluid"], locations={}, cell_function="cell-volume", current_domain="mixture")
        min_cell_volume = float(next(iter(min_volume_result.values())))
    field = read_fluent_ascii_export(raw)
    mean_pressure = float(np.mean([r["pressure"] for r in field]))
    mean_velocity = float(np.mean([r["velocity-magnitude"] for r in field]))
    log = (syc_dir / "scLog.scl").read_text(encoding="utf-8", errors="replace")
    mapped_pairs = re.findall(r"Mapped (?:Area|Elements|Nodes) \[%\].*?\|\s*([0-9.]+)\s+([0-9.]+)", log)
    mapped = [float(v) for pair in mapped_pairs for v in pair]
    iterations = [int(v) for v in re.findall(r"COUPLING ITERATION\s*=\s*(\d+)", log)]
    history_csv = run_dir / "tip_history.csv"
    with history_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(history[0])); writer.writeheader(); writer.writerows(history)
    checks = {
        "ten_time_steps": len(history) == 10, "mapping_100_percent": bool(mapped) and min(mapped) >= 99.9,
        "coupling_iterations_recorded": len(iterations) >= 10, "structure_moves": max_tip > 1e-5,
        "motion_feedback_changes_force": len({round(row["fluid_force_x_N"], 5) for row in history[5:]}) > 2,
        "force_conservation_lt_1pct": force_error < 0.01, "positive_cell_volume": min_cell_volume > 0,
        "fluid_fields_finite": np.isfinite(mean_pressure) and np.isfinite(mean_velocity),
        "stress_extracted": max_stress is not None and max_stress > 0,
    }
    checks = {key: bool(value) for key, value in checks.items()}
    payload = {
        "case": CASE, "benchmark": "Ansys official oscillating plate, shortened Student smoke",
        "participants": ["MAPDL", "Fluent"], "interface": "Interface-1",
        "data_transfers": ["Fluid Force -> MAPDL FORC", "MAPDL INCD -> Fluent displacement"],
        "mapping": {"minimum_percent": min(mapped)},
        "convergence": {"iteration_records": len(iterations), "maximum_iteration": max(iterations)},
        "results": {"synchronized_history": history, "final_max_nodal_displacement_m": max_tip, "final_max_equivalent_stress_Pa": max_stress, "final_mean_pressure_Pa": mean_pressure, "final_mean_velocity_m_s": mean_velocity, "final_force_conservation_relative": force_error, "minimum_dynamic_cell_volume_m3": min_cell_volume},
        "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
        "files": [str(interface_csv.resolve()), str((syc_dir/"scLog.scl").resolve()), str(raw.resolve()), str(history_csv.resolve())],
    }
    write_json(OUT / f"{CASE}.json", payload); print(payload)
    return 0 if payload["status"] == "PASS" else 1


def main() -> int:
    before = multiphysics_processes()
    run_dir = OUT / CASE
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"case": CASE, "benchmark": "Ansys official oscillating plate, shortened Student smoke"}
    try:
        with mapdl_session(working_dir=run_dir / "mapdl") as mapdl, fluent_session(
            dimension=3, processor_count=1, cwd=run_dir / "fluent", start_transcript=True
        ) as fluent, system_coupling_session(working_dir=run_dir / "system-coupling") as syc:
            mapdl.prep7()
            mapdl.mp("DENS", 1, 2550)
            mapdl.mp("ALPX", 1, 1.2e-5)
            mapdl.mp("EX", 1, 2.5e6)
            mapdl.mp("NUXY", 1, 0.35)
            mapdl.et(1, 186)
            mapdl.keyopt(1, 2, 1)
            mapdl.block(10.00, 10.06, 0.0, 1.0, 0.0, 0.4)
            mapdl.esize(0.10)
            mapdl.vsweep(1)
            mapdl.run("NSEL,S,LOC,Y,0")
            mapdl.d("all", "all")
            mapdl.nsel("S", "LOC", "X", 9.99, 10.01)
            mapdl.nsel("A", "LOC", "Y", 0.99, 1.01)
            mapdl.nsel("A", "LOC", "X", 10.05, 10.07)
            mapdl.cm("FSIN_1", "NODE")
            mapdl.sf("FSIN_1", "FSIN", 1)
            mapdl.allsel()
            mapdl.run("/SOLU")
            mapdl.antype(4)
            mapdl.nlgeom("ON")
            mapdl.kbc(1)
            mapdl.trnopt("full", "", "", "", "", "hht")
            mapdl.tintp(0.1)
            mapdl.autots("off")
            mapdl.run("nsub,1,1,1")
            mapdl.run("time,1.0")
            mapdl.timint("on")
            fluent.settings.file.read(file_type="case", file_name=str(ASSET))

            solid_name = syc.setup.add_participant(participant_session=mapdl)
            fluid_name = syc.setup.add_participant(participant_session=fluent)
            syc.setup.coupling_participant[solid_name].display_name = "Solid"
            syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
            interface_name = syc.setup.add_interface(
                side_one_participant=fluid_name, side_one_regions=["wall_deforming"],
                side_two_participant=solid_name, side_two_regions=["FSIN_1"]
            )
            transfer_names = syc.setup.add_fsi_data_transfers(interface=interface_name)
            force_transfer = syc.setup.coupling_interface[interface_name].data_transfer["FORC"]
            force_transfer.option = "UsingExpression"
            force_transfer.value = "vector(5.0 [N], 0.0 [N], 0.0 [N]) if Time < 0.5 [s] else force"
            syc.setup.solution_control.time_step_size = "0.1 [s]"
            syc.setup.solution_control.end_time = 1.0
            syc.setup.solution_control.maximum_iterations = 5
            syc.setup.output_control.option = "EveryStep"
            syc.setup.output_control.generate_csv_chart_output = True
            syc.solution.solve()

            times = np.asarray(mapdl.result.time_values, dtype=float)
            tip_history = []
            for index, time_value in enumerate(times):
                _ids, displacements = mapdl.result.nodal_displacement(index)
                tip_history.append({"time_s": float(time_value), "tip_x_displacement_m": float(np.max(displacements[:, 0]))})
            for i, row in enumerate(tip_history):
                if i == 0:
                    row["tip_velocity_m_s"] = 0.0
                else:
                    row["tip_velocity_m_s"] = (row["tip_x_displacement_m"] - tip_history[i-1]["tip_x_displacement_m"]) / (row["time_s"] - tip_history[i-1]["time_s"])
            integrals = fluent.settings.results.report.surface_integrals
            force_x = float("nan")  # populated from conservative System Coupling diagnostics below
            pressure = float(integrals.get_area_weighted_avg(surface_names=["wall_deforming"], report_of="pressure")["wall_deforming"])
            volume_result = fluent.settings.results.report.volume_integrals.get_volume_average(cell_zones=["part-fluid"], locations={}, cell_function="velocity-magnitude", current_domain="mixture")
            velocity = float(next(iter(volume_result.values())))
            fluent.settings.file.write_case_data(file_name=str(run_dir / "fluent" / "fsi_two_way.cas.h5"))
            mapdl.save(str(run_dir / "mapdl" / "fsi_two_way.db"))
        syc_dir = run_dir / "system-coupling" / "SyC"
        log = (syc_dir / "scLog.scl").read_text(encoding="utf-8", errors="replace")
        mapped_pairs = re.findall(r"Mapped (?:Area|Elements|Nodes) \[%\].*?\|\s*([0-9.]+)\s+([0-9.]+)", log)
        mapped = [float(v) for pair in mapped_pairs for v in pair]
        iterations = [int(v) for v in re.findall(r"COUPLING ITERATION\s*=\s*(\d+)", log)]
        interface_csv = syc_dir / "Interface-1.csv"
        with interface_csv.open(newline="", encoding="utf-8-sig") as stream:
            transfer_rows = list(csv.DictReader(stream))
        force_columns = [k for k in transfer_rows[-1] if "Force (Sum)" in k]
        disp_columns = [k for k in transfer_rows[-1] if "displacement (Weighted Average)" in k]
        fluid_force_columns=[k for k in force_columns if "Fluid" in k or "FLUENT" in k];solid_force_columns=[k for k in force_columns if "Solid" in k or "MAPDL" in k]
        fluid_force_vector=np.asarray([float(transfer_rows[-1][k]) for k in fluid_force_columns]);solid_force_vector=np.asarray([float(transfer_rows[-1][k]) for k in solid_force_columns]);force_x=float(fluid_force_vector[0])
        final_force_conservation = np.linalg.norm(fluid_force_vector-solid_force_vector) / max(np.linalg.norm(fluid_force_vector), 1e-30)
        history_csv = run_dir / "tip_history.csv"
        with history_csv.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(tip_history[0]))
            writer.writeheader(); writer.writerows(tip_history)
        displacement_values = [r["tip_x_displacement_m"] for r in tip_history]
        sign_changes = sum(np.sign(displacement_values[i]) != np.sign(displacement_values[i-1]) for i in range(1, len(displacement_values)))
        dynamic_mesh_ok = "negative cell volume" not in log.lower() and "dynamic mesh failed" not in log.lower()
        remaining = wait_for_process_cleanup(before)
        checks = {
            "two_participants": bool(solid_name and fluid_name), "force_and_displacement_transfers": len(transfer_names) == 2,
            "mapping_100_percent": bool(mapped) and min(mapped) >= 99.9,
            "coupling_iterations_recorded": len(iterations) >= len(tip_history),
            "transient_history": len(tip_history) >= 10, "plate_moves": max(map(abs, displacement_values)) > 1e-5,
            "motion_changes_after_release": len(set(round(v, 8) for v in displacement_values[5:])) > 2,
            "fluid_force_finite": np.isfinite(force_x), "pressure_finite": np.isfinite(pressure), "velocity_finite": np.isfinite(velocity),
            "dynamic_mesh_no_failure": dynamic_mesh_ok,
            "force_conservation_lt_1pct": final_force_conservation is not None and final_force_conservation < 0.01,
            "clean_shutdown": not remaining,
        }
        payload.update({
            "participants": [solid_name, fluid_name], "interface": interface_name, "data_transfers": list(transfer_names),
            "mapping": {"minimum_percent": min(mapped) if mapped else None},
            "convergence": {"iteration_records": len(iterations), "maximum_iteration": max(iterations) if iterations else None},
            "results": {"tip_history": tip_history, "max_tip_displacement_m": max(map(abs, displacement_values)), "sign_changes": sign_changes, "final_fluid_force_x_N": force_x, "final_mean_pressure_Pa": pressure, "final_mean_velocity_m_s": velocity, "force_conservation_relative": final_force_conservation, "dynamic_mesh_quality": "no negative-volume/dynamic-mesh failure in coupling log"},
            "checks": checks, "residual_processes": remaining, "status": "PASS" if all(checks.values()) else "FAIL",
            "files": [str((syc_dir / "scLog.scl").resolve()), str(interface_csv.resolve()), str(history_csv.resolve())],
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "residual_processes": wait_for_process_cleanup(before)})
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(postprocess_existing() if "--postprocess-existing" in sys.argv else main())
