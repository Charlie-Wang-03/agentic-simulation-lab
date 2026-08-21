"""Case J: Fluent-native finite-rate reacting flow with a conjugate solid wall."""

from __future__ import annotations

import numpy as np
from energy_accounting import compute_windowed_energy_balance, surface_heat_consistency, trapezoidal_integral
from fluent_mesh import write_fluent_ascii
from fluent_smoke_common import fluent_session, read_fluent_ascii_export
from phase_reactive_common import OUT, base_payload, ensure_dirs, write_json

CASE = "J"
L, HF, HS = 0.020, 0.004, 0.0015
NX, NYF, NYS = 20, 4, 2
U, TIN, TCOLD = 0.10, 1000.0, 900.0
YCH4, YO2 = 0.055, 0.220
DT = 0.005
BALANCE_WINDOW_INTERVALS = 10
ENERGY_BALANCE_THRESHOLD = 0.10


def _zone_integral(result, zone: str) -> float:
    """Extract one zone from a Fluent integral query without assuming a Net key."""
    if isinstance(result, dict):
        if zone in result:
            return float(result[zone])
        if "Net" in result:
            return float(result["Net"])
        if len(result) == 1:
            return float(next(iter(result.values())))
    return float(result)


def make_mesh(path):
    xs = [L * i / NX for i in range(NX + 1)]
    ys = [HF * j / NYF for j in range(NYF + 1)] + [HF + HS * j / NYS for j in range(1, NYS + 1)]
    points = [(x, y) for y in ys for x in xs]
    node = lambda i, j: j * len(xs) + i
    cells, zones = [], []
    for j in range(len(ys) - 1):
        for i in range(NX):
            cells.append((node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)))
            zones.append("reacting-fluid" if j < NYF else "solid-wall")
    def boundary(_nodes, c):
        x, y = c
        if abs(x) < 1e-12:
            return ("reactant-inlet", "velocity-inlet") if y < HF else ("solid-left", "wall")
        if abs(x - L) < 1e-12:
            return ("outlet", "pressure-outlet") if y < HF else ("solid-right", "wall")
        if abs(y) < 1e-12:
            return "fluid-bottom", "wall"
        if abs(y - HF - HS) < 1e-12:
            return "cold-outer-wall", "wall"
        raise ValueError(f"unclassified boundary {c}")
    return write_fluent_ascii(path, dimension=2, points=points, cells=cells, boundary_name=boundary,
                              cell_zone_names=zones, cell_zone_types={"reacting-fluid": "fluid", "solid-wall": "solid"})


def main() -> int:
    ensure_dirs()
    mesh = OUT / "case_j_reactive_cht.msh"
    stats = make_mesh(mesh)
    payload = base_payload(CASE, "Finite-rate reacting flow with conjugate solid heat transfer", "Ansys Fluent Student 2026 R1")
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh))
            s.settings.setup.general.solver.time = "unsteady-1st-order"
            s.settings.setup.models.viscous.model = "laminar"
            s.settings.setup.models.energy.enabled = True
            sp = s.settings.setup.models.species
            sp.model.option = "species-transport"
            sp.model.material = "methane-air"
            sp.reactions.enable_volumetric_reactions = True
            aluminum = s.settings.setup.materials.solid["aluminum"]
            aluminum.thermal_conductivity.value = 5.0
            s.settings.setup.cell_zone_conditions.solid["solid-wall"].material = "aluminum"
            inlet = s.settings.setup.boundary_conditions.velocity_inlet["reactant-inlet"]
            inlet.momentum.velocity_magnitude.value = U
            inlet.thermal.temperature.value = TIN
            for name, value in {"ch4": YCH4, "o2": YO2, "co2": 0.0, "h2o": 0.0}.items():
                inlet.species.species_mass_fraction[name].value = value
            cold = s.settings.setup.boundary_conditions.wall["cold-outer-wall"]
            cold.thermal.thermal_condition = "Temperature"
            cold.thermal.temperature.value = TCOLD
            for name in ("fluid-bottom", "solid-left", "solid-right"):
                wall = s.settings.setup.boundary_conditions.wall[name]
                wall.thermal.thermal_condition = "Heat Flux"
                wall.thermal.heat_flux.value = 0.0
            interface_names = [name for name in list(s.settings.setup.boundary_conditions.wall) if "interface" in name or "shadow" in name]
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.run_calculation.parameters.time_step_size = DT
            for _ in range(600 - BALANCE_WINDOW_INTERVALS):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
            volume_integrals = s.settings.results.report.volume_integrals
            integrals = s.settings.results.report.surface_integrals

            def stored_energy() -> tuple[float, dict[str, float]]:
                # Total enthalpy aligns the reacting-fluid storage with the boundary
                # flux. The solid has zero velocity and uses its static enthalpy.
                components = {
                    zone: _zone_integral(
                        volume_integrals.get_mass_integral(
                            cell_zones=[zone], locations={}, cell_function=quantity, current_domain="mixture"
                        ), zone,
                    )
                    for zone, quantity in (("reacting-fluid", "total-enthalpy"), ("solid-wall", "enthalpy"))
                }
                return sum(components.values()), components

            def accounting_snapshot() -> dict[str, object]:
                flows = integrals.get_mass_flow_rate(surface_names=["reactant-inlet", "outlet"])
                raw_in = float(flows["reactant-inlet"])
                raw_out = float(flows["outlet"])
                bulk_h_snapshot = integrals.get_mass_weighted_avg(
                    surface_names=["reactant-inlet", "outlet"], report_of="total-enthalpy"
                )
                raw_wall_heat = float(
                    integrals.get_integral(
                        surface_names=["cold-outer-wall"], report_of="heat-flux"
                    )["cold-outer-wall"]
                )
                energy, components = stored_energy()
                return {
                    # PyFluent's per-zone report sign presentation is preserved
                    # separately. Accounting direction comes from the explicitly
                    # selected inlet and outlet roles.
                    "mass_flow_in": abs(raw_in),
                    "mass_flow_out": abs(raw_out),
                    "raw_mass_flow_in": raw_in,
                    "raw_mass_flow_out": raw_out,
                    "inlet_total_enthalpy": float(bulk_h_snapshot["reactant-inlet"]),
                    "outlet_total_enthalpy": float(bulk_h_snapshot["outlet"]),
                    # The final exported signed field independently verifies that
                    # this cold boundary is outward heat transfer.
                    "wall_heat_out": abs(raw_wall_heat),
                    "raw_wall_heat": raw_wall_heat,
                    "stored_energy": energy,
                    "stored_energy_components": components,
                }

            accounting_samples = [accounting_snapshot()]
            for _ in range(BALANCE_WINDOW_INTERVALS):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
                accounting_samples.append(accounting_snapshot())
            window_balance = compute_windowed_energy_balance(
                accounting_samples, time_step=DT, threshold=ENERGY_BALANCE_THRESHOLD
            )
            final_step_balance = compute_windowed_energy_balance(
                accounting_samples[-2:], time_step=DT, threshold=ENERGY_BALANCE_THRESHOLD
            )
            final_accounting = accounting_samples[-1]
            allowed = list(s.fields.field_data.scalar_fields.allowed_values())
            reaction_field = next((v for v in allowed if "reaction" in v.lower() and "rate" in v.lower()), None)
            qfield = next((v for v in ("wall-heat-flux", "surface-heat-flux", "heat-flux") if v in allowed), None)
            fluid_raw = OUT / "case_j_fluid.csv"
            fluid_quantities = ["x-coordinate", "y-coordinate", "temperature", "x-velocity", "y-velocity", "pressure", "ch4", "o2", "co2", "h2o", "n2"]
            if reaction_field:
                fluid_quantities.append(reaction_field)
            s.settings.file.export.ascii(file_name=str(fluid_raw), surface_name_list=["interior-reacting-fluid", "reactant-inlet", "outlet"],
                                         delimiter="comma", quantities=fluid_quantities, location="node")
            solid_raw = OUT / "case_j_solid.csv"
            solid_surfaces = ["interior-solid-wall", "cold-outer-wall"] + interface_names
            solid_quantities = ["x-coordinate", "y-coordinate", "temperature"] + ([qfield] if qfield else [])
            s.settings.file.export.ascii(file_name=str(solid_raw), surface_name_list=list(dict.fromkeys(solid_surfaces)),
                                         delimiter="comma", quantities=solid_quantities, location="node")
            bulk_h = integrals.get_mass_weighted_avg(surface_names=["reactant-inlet", "outlet"], report_of="total-enthalpy")
            bulk_species = {name: integrals.get_mass_weighted_avg(surface_names=["reactant-inlet", "outlet"], report_of=name)
                            for name in ("ch4", "o2", "co2", "h2o", "n2")}
            s.settings.file.write_case_data(file_name=str(OUT / "case_j.cas.h5"))
        fluid = list({(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in read_fluent_ascii_export(fluid_raw)}.values())
        solid = list({(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in read_fluent_ascii_export(solid_raw)}.values())
        outlet = [r for r in fluid if abs(r["x-coordinate"] - L) < 1e-9]
        yout = {n: float(bulk_species[n]["outlet"]) for n in ("ch4", "o2", "co2", "h2o", "n2")}
        sums = np.asarray([sum(r[n] for n in ("ch4", "o2", "co2", "h2o", "n2")) for r in fluid])
        reaction_peak = max(abs(r[reaction_field]) for r in fluid) if reaction_field else 0.0
        mdot_in = float(final_accounting["mass_flow_in"])
        mdot_out = float(final_accounting["mass_flow_out"])
        carbon_in_fraction = float(bulk_species["ch4"]["reactant-inlet"]) * 12.011 / 16.04303 + float(bulk_species["co2"]["reactant-inlet"]) * 12.011 / 44.00995
        carbon_out_fraction = yout["ch4"] * 12.011 / 16.04303 + yout["co2"] * 12.011 / 44.00995
        carbon_in_rate = mdot_in * carbon_in_fraction
        carbon_out_rate = mdot_out * carbon_out_fraction
        carbon_error = abs(carbon_out_rate - carbon_in_rate) / max(carbon_in_rate, 1e-30)
        cold_rows = sorted([r for r in solid if abs(r["y-coordinate"] - HF - HS) < 1e-9], key=lambda r: r["x-coordinate"])
        if not qfield or not cold_rows:
            raise ValueError("cold-wall heat-flux field is unavailable")
        raw_exported_wall_heat = trapezoidal_integral(
            [r[qfield] for r in cold_rows], [r["x-coordinate"] for r in cold_rows]
        )
        if raw_exported_wall_heat >= 0:
            raise ValueError("unexpected exported wall heat-flux sign")
        exported_wall_heat_out = -raw_exported_wall_heat
        heat_consistency = surface_heat_consistency(
            native_heat_out=float(final_accounting["wall_heat_out"]),
            exported_heat_out=exported_wall_heat_out,
        )
        mass_flow_error = abs(mdot_in - mdot_out) / max(0.5 * (mdot_in + mdot_out), 1e-30)
        checks = {
            "native_finite_rate_reaction_nonzero": reaction_field is not None and reaction_peak > 0,
            "solid_temperature_responds": max(r["temperature"] for r in solid) - min(r["temperature"] for r in solid) > 1.0,
            "outer_wall_heat_transfer_positive": float(final_accounting["wall_heat_out"]) > 0,
            "native_exported_wall_heat_agree_lt_10pct": heat_consistency["relative_difference"] < 0.10,
            "interface_created": len(interface_names) >= 1,
            "species_sum_error_lt_1e-4": float(np.max(np.abs(sums - 1.0))) < 1e-4,
            "carbon_balance_lt_5pct": carbon_error < 0.05,
            "mass_flow_balance_lt_1pct": mass_flow_error < 0.01,
            "global_total_enthalpy_balance_lt_10pct": bool(window_balance["passes"]),
        }
        payload.update({
            "model": {"chemistry": "Fluent methane-air one-step finite-rate", "energy": True, "conjugate_domains": ["reacting-fluid", "solid-wall"],
                      "solid_conductivity_W_mK": 5.0, "outer_wall_temperature_K": TCOLD,
                      "time_integration": {"dt_s": DT, "steps": 600, "final_time_s": 3.0}},
            "diagnostic": {"targeted_retest": 2, "hypothesis": "H3_final_step_storage_sampling_noise",
                           "rationale": "use a predeclared 10-step window with matching trapezoidal boundary-flux averages; preserve the 10% threshold and all model/numerical settings"},
            "mesh": {**stats, "fluid_cells": NX * NYF, "solid_cells": NX * NYS}, "interfaces": interface_names,
            "results": {"outlet_mass_fractions": yout, "outlet_temperature_K": float(np.mean([r["temperature"] for r in outlet])),
                        "maximum_fluid_temperature_K": max(r["temperature"] for r in fluid),
                        "solid_temperature_range_K": [min(r["temperature"] for r in solid), max(r["temperature"] for r in solid)],
                        "peak_reaction_rate": reaction_peak, "outer_wall_heat_W_per_m": exported_wall_heat_out,
                        "mass_flow_in_kg_s_per_m": mdot_in, "mass_flow_out_kg_s_per_m": mdot_out,
                        "mass_flow_balance_relative_error": mass_flow_error,
                        "inlet_total_enthalpy_J_kg": float(bulk_h["reactant-inlet"]),
                        "outlet_total_enthalpy_J_kg": float(bulk_h["outlet"]),
                        "total_enthalpy_flux_drop_W_per_m": window_balance["advective_enthalpy_net_in_W_per_m"],
                        "integrated_outer_wall_heat_W_per_m": window_balance["wall_heat_out_W_per_m"],
                        "stored_enthalpy_before_window_J_per_m": accounting_samples[0]["stored_energy"],
                        "stored_enthalpy_after_window_J_per_m": accounting_samples[-1]["stored_energy"],
                        "transient_enthalpy_accumulation_W_per_m": window_balance["accumulation_W_per_m"],
                        "global_energy_residual_W_per_m": window_balance["residual_W_per_m"],
                        "global_total_enthalpy_balance_relative_error": window_balance["relative_error"],
                        "energy_balance_window": window_balance,
                        "final_step_energy_balance": final_step_balance,
                        "wall_heat_surface_consistency": heat_consistency,
                        "fluent_raw_signs": {"mass_flow_in": final_accounting["raw_mass_flow_in"],
                                             "mass_flow_out": final_accounting["raw_mass_flow_out"],
                                             "native_wall_heat": final_accounting["raw_wall_heat"],
                                             "exported_wall_heat": raw_exported_wall_heat},
                        "report_direction_basis": "PyFluent per-zone mass-flow and integral magnitudes are assigned by explicit inlet/outlet/cold-wall roles; exported heat-flux sign independently confirms outward heat",
                        "stored_energy_components_J_per_m": final_accounting["stored_energy_components"],
                        "energy_balance_qualification": "unit-depth fluid+solid control volume; total-enthalpy advection, outward wall heat, and fixed-window stored-energy accumulation",
                        "carbon_balance_relative_error": carbon_error, "max_species_sum_error": float(np.max(np.abs(sums - 1.0)))},
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
            "files": [p.relative_to(OUT.parent).as_posix() for p in (mesh, fluid_raw, solid_raw, OUT / "case_j.cas.h5")],
        })
    except Exception as exc:  # noqa: BLE001 - solver/API failures must become durable FAIL evidence
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_j.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
