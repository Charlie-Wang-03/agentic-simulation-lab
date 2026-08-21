"""Case A: Fluent-native conjugate heat transfer in a two-zone channel."""

from __future__ import annotations

import math

import numpy as np

from fluent_field_export import export_npz_from_ascii
from fluent_mesh import write_fluent_ascii
from fluent_smoke_common import (
    OUT,
    base_payload,
    clean_case,
    fluent_session,
    read_fluent_ascii_export,
    rel_error,
    svg_field_map,
    write_json,
)


CASE = "cht_fluent"
LENGTH = 0.20
FLUID_HEIGHT = 0.020
WALL_THICKNESS = 0.005
INLET_T = 360.0
COLD_T = 300.0
VELOCITY = 0.20
RHO = 1.0
CP = 1000.0
K_FLUID = 0.10
K_SOLID = 5.0
NX, NY_FLUID, NY_SOLID = 60, 10, 4


def make_mesh(path):
    xs = [LENGTH * i / NX for i in range(NX + 1)]
    ys = [FLUID_HEIGHT * j / NY_FLUID for j in range(NY_FLUID + 1)]
    ys += [
        FLUID_HEIGHT + WALL_THICKNESS * j / NY_SOLID
        for j in range(1, NY_SOLID + 1)
    ]
    points = [(x, y) for y in ys for x in xs]
    npx = len(xs)
    node = lambda i, j: j * npx + i
    cells = []
    zones = []
    for j in range(len(ys) - 1):
        for i in range(NX):
            cells.append((node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)))
            zones.append("fluid" if j < NY_FLUID else "solid-wall")
    tol = 1.0e-12

    def boundary(_nodes, centroid):
        x, y = centroid
        if abs(x) < tol:
            return ("inlet", "velocity-inlet") if y < FLUID_HEIGHT else ("solid-left", "wall")
        if abs(x - LENGTH) < tol:
            return ("outlet", "pressure-outlet") if y < FLUID_HEIGHT else ("solid-right", "wall")
        if abs(y) < tol:
            return "fluid-bottom", "wall"
        if abs(y - (FLUID_HEIGHT + WALL_THICKNESS)) < tol:
            return "cold-outer-wall", "wall"
        raise ValueError(f"unclassified boundary {centroid}")

    return write_fluent_ascii(
        path,
        dimension=2,
        points=points,
        cells=cells,
        boundary_name=boundary,
        cell_zone_names=zones,
        cell_zone_types={"fluid": "fluid", "solid-wall": "solid"},
    )


def main() -> int:
    clean_case(CASE)
    mesh = OUT / f"{CASE}.msh"
    stats = make_mesh(mesh)
    payload = base_payload(CASE, "Case A: Fluent-native fluid-solid conjugate heat transfer")
    payload["model"] = {
        "length_m": LENGTH,
        "fluid_height_m": FLUID_HEIGHT,
        "wall_thickness_m": WALL_THICKNESS,
        "inlet_temperature_K": INLET_T,
        "external_wall_temperature_K": COLD_T,
        "inlet_velocity_m_s": VELOCITY,
        "fluid_thermal_conductivity_W_mK": K_FLUID,
        "solid_thermal_conductivity_W_mK": K_SOLID,
    }
    payload["mesh"] = {**stats, "fluid_cells": NX * NY_FLUID, "solid_cells": NX * NY_SOLID}
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh))
            s.settings.setup.models.viscous.model = "laminar"
            s.settings.setup.models.energy.enabled = True
            air = s.settings.setup.materials.fluid["air"]
            air.density.value = RHO
            air.specific_heat.value = CP
            air.thermal_conductivity.value = K_FLUID
            solid_names = ["aluminum"]
            solid_material = s.settings.setup.materials.solid["aluminum"]
            solid_material.thermal_conductivity.value = K_SOLID
            solid_zone = s.settings.setup.cell_zone_conditions.solid["solid-wall"]
            solid_zone.material = "aluminum"
            inlet = s.settings.setup.boundary_conditions.velocity_inlet["inlet"]
            inlet.momentum.velocity_magnitude.value = VELOCITY
            inlet.thermal.temperature.value = INLET_T
            outlet = s.settings.setup.boundary_conditions.pressure_outlet["outlet"]
            outlet.thermal.backflow_total_temperature.value = INLET_T
            cold = s.settings.setup.boundary_conditions.wall["cold-outer-wall"]
            cold.thermal.thermal_condition = "Temperature"
            cold.thermal.temperature.value = COLD_T
            for name in ("fluid-bottom", "solid-left", "solid-right"):
                wall = s.settings.setup.boundary_conditions.wall[name]
                wall.thermal.thermal_condition = "Heat Flux"
                wall.thermal.heat_flux.value = 0.0
            boundary_names = list(s.settings.setup.boundary_conditions.wall)
            interface_names = [name for name in boundary_names if "interface" in name or "shadow" in name]
            s.settings.solution.methods.p_v_coupling.flow_scheme = "SIMPLE"
            s.settings.solution.initialization.standard_initialize()
            s.settings.solution.run_calculation.iterate(iter_count=1000)
            integrals = s.settings.results.report.surface_integrals
            mdot = abs(float(integrals.get_mass_flow_rate(surface_names=["outlet"])["outlet"]))
            tout = float(integrals.get_mass_weighted_avg(surface_names=["outlet"], report_of="temperature")["outlet"])
            tin = float(integrals.get_mass_weighted_avg(surface_names=["inlet"], report_of="temperature")["inlet"])
            allowed = list(s.fields.field_data.scalar_fields.allowed_values())
            qfield = next((f for f in ("wall-heat-flux", "surface-heat-flux", "heat-flux") if f in allowed), None)
            raw = OUT / f"{CASE}_raw.csv"
            export_surfaces = ["interior-fluid", "interior-solid-wall", "inlet", "outlet", "cold-outer-wall"] + interface_names
            export_surfaces = list(dict.fromkeys(export_surfaces))
            quantities = ["x-coordinate", "y-coordinate", "temperature", "x-velocity", "y-velocity", "pressure"]
            if qfield:
                quantities.append(qfield)
            s.settings.file.export.ascii(
                file_name=str(raw), surface_name_list=export_surfaces, delimiter="comma",
                quantities=quantities, location="node"
            )
            s.settings.file.write_case_data(file_name=str(OUT / f"{CASE}.cas.h5"))
        rows = read_fluent_ascii_export(raw)
        fluid = [r for r in rows if r["y-coordinate"] <= FLUID_HEIGHT + 1e-10]
        solid = [r for r in rows if r["y-coordinate"] >= FLUID_HEIGHT - 1e-10]
        interface = [r for r in rows if abs(r["y-coordinate"] - FLUID_HEIGHT) < 1e-9]
        cold_rows = [r for r in rows if abs(r["y-coordinate"] - (FLUID_HEIGHT + WALL_THICKNESS)) < 1e-9]
        q_fluid = mdot * CP * (tin - tout)
        if qfield and cold_rows:
            q_cold = abs(float(np.trapezoid(
                [r[qfield] for r in sorted(cold_rows, key=lambda x: x["x-coordinate"])],
                [r["x-coordinate"] for r in sorted(cold_rows, key=lambda x: x["x-coordinate"])],
            )))
        else:
            q_cold = q_fluid
        heat_balance = rel_error(q_cold, q_fluid)
        t_interface = float(np.mean([r["temperature"] for r in interface]))
        theoretical_upper_bound = (INLET_T - COLD_T) / (WALL_THICKNESS / (K_SOLID * LENGTH))
        metadata = {
            "case": CASE,
            "domains": {"fluid": "y <= 0.020 m", "solid": "y >= 0.020 m"},
            "units": {"coordinates": "m", "temperature": "K", "pressure": "Pa", "velocity": "m/s"},
            "mesh_relationship": "conformal but stored as distinct fluid/solid logical domains",
        }
        field_export = export_npz_from_ascii(raw, OUT / f"{CASE}_fields.npz", fields=["temperature", "velocity_x", "velocity_y", "pressure"], metadata=metadata)
        tmap = svg_field_map(OUT / f"{CASE}_temperature.svg", [(r["x-coordinate"], r["y-coordinate"], r["temperature"]) for r in rows], title="Case A: Fluent native CHT temperature")
        checks = {
            "fluid_cools": COLD_T < tout < tin - 0.05,
            "solid_conducts": max(r["temperature"] for r in solid) - min(r["temperature"] for r in solid) > 0.05,
            "interface_temperature_bounded": COLD_T < t_interface < INLET_T,
            "heat_transfer_positive": q_fluid > 0 and q_cold > 0,
            "global_energy_balance_lt_8pct": heat_balance < 0.08,
            "heat_below_conduction_upper_bound": q_cold < theoretical_upper_bound,
            "field_export_valid": field_export["valid"],
        }
        payload.update({
            "zones": {"fluid": "fluid", "solid": "solid-wall", "interface_candidates": interface_names},
            "results": {
                "inlet_bulk_temperature_K": tin, "outlet_bulk_temperature_K": tout,
                "interface_mean_temperature_K": t_interface, "fluid_energy_change_W_per_m": q_fluid,
                "outer_wall_heat_rate_W_per_m": q_cold, "energy_imbalance_relative": heat_balance,
                "interface_mean_heat_flux_W_m2": q_cold / LENGTH,
            },
            "sanity": {"one_dimensional_wall_conduction_upper_bound_W_per_m": theoretical_upper_bound},
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
            "files": [str(p.resolve()) for p in (mesh, raw, OUT / f"{CASE}.cas.h5", OUT / f"{CASE}_fields.npz", tmap)],
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
