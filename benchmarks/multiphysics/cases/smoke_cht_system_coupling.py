"""Case B: Fluent-MAPDL partitioned conjugate heat transfer via System Coupling."""

from __future__ import annotations

import re
import csv
from pathlib import Path

import numpy as np

from fluent_smoke_common import fluent_session
from multiphysics_common import (
    OUT,
    mapdl_session,
    multiphysics_processes,
    system_coupling_session,
    wait_for_process_cleanup,
    write_json,
)


CASE = "cht_system_coupling"
ASSET = OUT / "official_assets" / "fluid_domain.msh"


def parse_mapping_and_iterations(run_dir: Path) -> dict:
    texts = []
    for path in run_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".log", ".out", ".txt", ".csv", ".scl", ".dat"}:
            try:
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    joined = "\n".join(texts)
    mapped_pairs = re.findall(r"Mapped (?:Area|Elements|Nodes) \[%\].*?\|\s*([0-9.]+)\s+([0-9.]+)", joined)
    mapped = [float(value) for pair in mapped_pairs for value in pair]
    iteration_rows = re.findall(r"COUPLING ITERATION\s*=\s*(\d+)", joined, re.I)
    interface_csv = run_dir / "system-coupling" / "SyC" / "Interface-1.csv"
    final_row = None
    if interface_csv.is_file():
        with interface_csv.open(newline="", encoding="utf-8-sig") as stream:
            csv_rows = list(csv.DictReader(stream))
        final_row = csv_rows[-1] if csv_rows else None
    source_heat = float(final_row["Heat_Flow (Sum): Fluid"]) if final_row else None
    target_heat = float(final_row["Heat_Flow (Sum): Solid"]) if final_row else None
    heat_error = abs(source_heat-target_heat)/max(abs(source_heat), 1e-30) if final_row else None
    convergence_columns = [key for key in (final_row or {}) if key.startswith("Data Transfer Convergence")]
    return {
        "minimum_mapped_percent": min(mapped) if mapped else None,
        "mapping_values_found": len(mapped),
        "coupling_iteration_records": len(iteration_rows),
        "maximum_coupling_iteration": max(map(int, iteration_rows)) if iteration_rows else None,
        "final_transfer_convergence": {key: float(final_row[key]) for key in convergence_columns} if final_row else {},
        "final_heat_flow_source_W": source_heat,
        "final_heat_flow_target_W": target_heat,
        "interface_heat_conservation_relative": heat_error,
        "artifact_files": [str(p.resolve()) for p in (
            run_dir / "system-coupling" / "SyC" / "scLog.scl",
            run_dir / "system-coupling" / "SyC" / "chart.dat",
            interface_csv,
        ) if p.is_file()],
    }


def main() -> int:
    before = multiphysics_processes()
    run_dir = OUT / CASE
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "case": CASE,
        "participants": {"fluid": "Fluent 261", "solid": "MAPDL 261 thermal"},
        "asset": str(ASSET.resolve()),
        "data_transfers": [
            {"source": "MAPDL TEMP", "target": "Fluent temperature", "direction": "Solid -> Fluid"},
            {"source": "Fluent heatflow", "target": "MAPDL HFLW", "direction": "Fluid -> Solid"},
        ],
    }
    try:
        if not ASSET.is_file():
            raise FileNotFoundError(f"official CHT mesh missing: {ASSET}")
        with mapdl_session(working_dir=run_dir / "mapdl") as mapdl, fluent_session(
            dimension=3, processor_count=1, cwd=run_dir / "fluent", start_transcript=False
        ) as fluent, system_coupling_session(working_dir=run_dir / "system-coupling") as syc:
            mapdl.clear()
            mapdl.prep7()
            mapdl.mp("EX", 1, 69e9)
            mapdl.mp("NUXY", 1, 0.33)
            mapdl.mp("DENS", 1, 2700)
            mapdl.mp("ALPX", 1, 23.6e-6)
            mapdl.mp("KXX", 1, 237)
            mapdl.mp("C", 1, 900)
            mapdl.et(1, 279)
            mapdl.keyopt(1, 2, 1)
            mapdl.cyl4(0, 0, rad1=0.025, rad2=0.035, depth=0.2)
            mapdl.esize(0.004)
            mapdl.vsweep(1)
            mapdl.asel("S", "AREA", "", 5, 6)
            mapdl.nsla("S", 1)
            mapdl.cm("FSIN_1", "NODE")
            mapdl.allsel()
            mapdl.asel("S", "AREA", "", 3, 4)
            mapdl.cm("Outer_wall", "AREA")
            mapdl.allsel()
            mapdl.asel("S", "AREA", "", 2)
            mapdl.cm("Outlet", "AREA")
            mapdl.allsel()
            mapdl.asel("S", "AREA", "", 1)
            mapdl.cm("Inlet", "AREA")
            mapdl.allsel()
            mapdl.cmsel("S", "Outer_wall")
            mapdl.d("Outer_wall", "TEMP", 77)
            mapdl.allsel()
            for component in ("Inlet", "Outlet"):
                mapdl.cmsel("S", component)
                mapdl.sf("ALL", "HFLUX", 0)
                mapdl.allsel()
            mapdl.cmsel("S", "FSIN_1")
            mapdl.sf("FSIN_1", "FSIN", 1)
            mapdl.allsel()
            mapdl.run("/SOLU")
            mapdl.antype(0)

            fluent.settings.file.read(file_type="mesh", file_name=str(ASSET))
            fluent.settings.setup.models.energy.enabled = True
            fluent.settings.setup.materials.database.copy_by_name(type="fluid", name="water-liquid")
            fluent.settings.setup.cell_zone_conditions.fluid["fff_fluiddomain"].general.material = "water-liquid"
            fluent.settings.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity_magnitude = 0.1
            fluent.settings.setup.boundary_conditions.velocity_inlet["inlet"].thermal.temperature = 300
            fluent.settings.setup.boundary_conditions.wall["inner_wall"].thermal.thermal_condition = "via System Coupling"
            fluent.solution.run_calculation.iter_count = 15

            fluid_name = syc.setup.add_participant(participant_session=fluent)
            solid_name = syc.setup.add_participant(participant_session=mapdl)
            syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
            syc.setup.coupling_participant[solid_name].display_name = "Solid"
            interface_name = syc.setup.add_interface(
                side_one_participant=fluid_name, side_one_regions=["inner_wall"],
                side_two_participant=solid_name, side_two_regions=["FSIN_1"]
            )
            temperature_transfer = syc.setup.add_data_transfer(
                interface=interface_name, target_side="One", source_variable="TEMP", target_variable="temperature"
            )
            heat_transfer = syc.setup.add_data_transfer(
                interface=interface_name, target_side="Two", source_variable="heatflow", target_variable="HFLW"
            )
            syc.setup.solution_control.time_step_size = "0.1 [s]"
            syc.setup.solution_control.end_time = 0.5
            syc.setup.solution_control.maximum_iterations = 5
            syc.setup.output_control.option = "EveryStep"
            syc.setup.output_control.generate_csv_chart_output = True
            syc.solution.solve()

            integrals = fluent.settings.results.report.surface_integrals
            tout = float(integrals.get_mass_weighted_avg(surface_names=["outlet"], report_of="temperature")["outlet"])
            interface_t = float(integrals.get_area_weighted_avg(surface_names=["inner_wall"], report_of="temperature")["inner_wall"])
            allowed = list(fluent.fields.field_data.scalar_fields.allowed_values())
            qfield = next((f for f in ("wall-heat-flux", "surface-heat-flux", "heat-flux") if f in allowed), None)
            qavg = float(integrals.get_area_weighted_avg(surface_names=["inner_wall"], report_of=qfield)["inner_wall"]) if qfield else float("nan")
            area = float(integrals.get_area(surface_names=["inner_wall"])["inner_wall"])
            interface_heat = abs(qavg * area)
            mapdl.post1()
            mapdl.set("LAST")
            solid_temperatures_c = np.asarray(mapdl.post_processing.nodal_temperature(), dtype=float)
            solid_mean_k = float(np.mean(solid_temperatures_c) + 273.15)
            fluent.settings.file.write_case_data(file_name=str(run_dir / "fluent" / "cht_coupled.cas.h5"))
            mapdl.save(str(run_dir / "mapdl" / "cht_coupled.db"))
            participant_names = [fluid_name, solid_name]
        diagnostics = parse_mapping_and_iterations(run_dir)
        remaining = wait_for_process_cleanup(before)
        checks = {
            "two_participants_registered": len(participant_names) == 2,
            "interface_created": bool(interface_name),
            "two_data_transfers": bool(temperature_transfer) and bool(heat_transfer),
            "fluid_heats": tout > 300.0,
            "interface_temperature_physical": 300.0 < interface_t < 350.5,
            "solid_temperature_physical": 273.15 < solid_mean_k <= 350.5,
            "interface_heat_nonzero": interface_heat > 0,
            "mapping_artifact_present": diagnostics["mapping_values_found"] > 0,
            "coupling_iterations_recorded": diagnostics["coupling_iteration_records"] > 0,
            "interface_heat_conservation_lt_0_1pct": diagnostics["interface_heat_conservation_relative"] is not None and diagnostics["interface_heat_conservation_relative"] < 0.001,
            "clean_shutdown": not remaining,
        }
        payload.update({
            "system_coupling": {"interface": interface_name, "participants": participant_names, **diagnostics},
            "results": {
                "fluid_outlet_temperature_K": tout, "interface_temperature_K": interface_t,
                "solid_mean_temperature_K": solid_mean_k, "interface_area_m2": area,
                "interface_mean_heat_flux_W_m2": qavg, "interface_heat_flow_W": interface_heat,
            },
            "checks": checks, "residual_processes": remaining,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
        payload["residual_processes"] = wait_for_process_cleanup(before)
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
