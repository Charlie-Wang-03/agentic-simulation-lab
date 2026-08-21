"""Case F: native Fluent finite-rate methane-air reacting channel."""

from __future__ import annotations

import math
import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import fluent_session, read_fluent_ascii_export
from phase_reactive_common import OUT, base_payload, ensure_dirs, write_json


CASE = "F"
L, H, U, TIN = 0.02, 0.004, 0.10, 1000.0
YCH4, YO2 = 0.055, 0.220


def species_field(allowed: list[str], name: str) -> str:
    if name in allowed:
        return name
    values = [x for x in allowed if name in x.lower() and ("mass" in x.lower() or "fraction" in x.lower())]
    if not values: raise RuntimeError(f"No field for species {name}")
    return values[0]


def main() -> int:
    ensure_dirs(); mesh = OUT / "case_f_reactor.msh"
    xs = [L * i / 20 for i in range(21)]; ys = [H * j / 4 for j in range(5)]
    stats = rectangular_2d(mesh, xs, ys, left=("reactant-inlet", "velocity-inlet"),
                           right=("outlet", "pressure-outlet"), bottom=("bottom-wall", "wall"), top=("top-wall", "wall"))
    payload = base_payload(CASE, "Finite-rate methane-air channel reactor", "Ansys Fluent Student 2026 R1")
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.general.solver.time = "unsteady-1st-order"
            s.settings.setup.models.viscous.model = "laminar"
            s.settings.setup.models.energy.enabled = True
            sp = s.settings.setup.models.species; sp.model.option = "species-transport"; sp.model.material = "methane-air"
            sp.reactions.enable_volumetric_reactions = True
            inlet = s.settings.setup.boundary_conditions.velocity_inlet["reactant-inlet"]
            inlet.momentum.velocity_magnitude.value = U; inlet.thermal.temperature.value = TIN
            mf = inlet.species.species_mass_fraction
            for name, value in {"ch4": YCH4, "o2": YO2, "co2": 0.0, "h2o": 0.0}.items(): mf[name].value = value
            for name in ("bottom-wall", "top-wall"):
                w = s.settings.setup.boundary_conditions.wall[name]
                w.thermal.thermal_condition = "Temperature"; w.thermal.temperature.value = TIN
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.run_calculation.parameters.time_step_size = 0.001
            for _ in range(500):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
            allowed = list(s.fields.field_data.scalar_fields.allowed_values())
            fields = {name: species_field(allowed, name) for name in ("ch4", "o2", "co2", "h2o", "n2")}
            reaction_field = next((x for x in allowed if "reaction" in x.lower() and "rate" in x.lower()), None)
            heat_field = next((x for x in allowed if "heat" in x.lower() and ("source" in x.lower() or "release" in x.lower())), None)
            quantities = ["x-coordinate", "y-coordinate", "temperature", "x-velocity", "y-velocity", "pressure", *fields.values()]
            for x in (reaction_field, heat_field):
                if x and x not in quantities: quantities.append(x)
            raw = OUT / "case_f_final.csv"
            s.settings.file.export.ascii(file_name=str(raw), surface_name_list=["interior", "reactant-inlet", "outlet"],
                delimiter="comma", quantities=quantities, location="node")
            integrals = s.settings.results.report.surface_integrals
            mdot = abs(float(integrals.get_mass_flow_rate(surface_names=["outlet"])["outlet"]))
            bulk_h = integrals.get_mass_weighted_avg(surface_names=["reactant-inlet", "outlet"], report_of="total-enthalpy")
            wall_heat = abs(float(integrals.get_integral(surface_names=["bottom-wall", "top-wall"], report_of="heat-flux")["Net"]))
            s.settings.file.write_case_data(file_name=str(OUT / "case_f.cas.h5"))
        rows = read_fluent_ascii_export(raw)
        uniq = {(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in rows}; vals = list(uniq.values())
        outlet = [r for r in vals if abs(r["x-coordinate"] - L) < 1e-9]
        yout = {name: float(np.mean([r[field] for r in outlet])) for name, field in fields.items()}
        sums = np.asarray([sum(r[f] for f in fields.values()) for r in vals])
        conversion = 1.0 - yout["ch4"] / YCH4
        tmax = max(r["temperature"] for r in vals); tout = float(np.mean([r["temperature"] for r in outlet]))
        reaction_peak = max(abs(r[reaction_field]) for r in vals) if reaction_field else math.nan
        heat_peak = max(abs(r[heat_field]) for r in vals) if heat_field else None
        # Elemental C balance for CH4 -> CO2 using mass-fraction carbon content.
        carbon_out = yout["ch4"] * 12.011 / 16.04303 + yout["co2"] * 12.011 / 44.00995
        carbon_in = YCH4 * 12.011 / 16.04303
        carbon_error = abs(carbon_out - carbon_in) / carbon_in
        total_enthalpy_flux_drop = mdot * (float(bulk_h["reactant-inlet"]) - float(bulk_h["outlet"]))
        energy_error = abs(total_enthalpy_flux_drop - wall_heat) / max(wall_heat, 1e-30)
        checks = {"native_finite_rate_model": True, "reaction_rate_field_available": reaction_field is not None,
                  "temperature_rises_gt_10K": tmax > TIN + 10, "fuel_conversion_gt_5pct": conversion > 0.05,
                  "species_bounded": all(-1e-5 <= r[f] <= 1 + 1e-5 for r in vals for f in fields.values()),
                  "species_sum_error_lt_1e-4": float(np.max(np.abs(sums - 1))) < 1e-4,
                  "carbon_balance_lt_5pct": carbon_error < 0.05,
                  "global_total_enthalpy_balance_lt_5pct": energy_error < 0.05,
                  "reaction_rate_nonzero": reaction_field is not None and reaction_peak > 0}
        payload.update({"model": {"species_transport": True, "volumetric_reactions": True,
                        "chemistry": "finite-rate", "mechanism": "Fluent methane-air one-step",
                        "time_integration": {"scheme": "first-order implicit", "dt_s": 0.001, "steps": 500, "final_time_s": 0.5},
                        "species_names": list(fields), "inlet": {"Y_CH4": YCH4, "Y_O2": YO2, "temperature_K": TIN, "velocity_m_s": U}},
                        "mesh": stats, "results": {"outlet_mass_fractions": yout, "fuel_conversion": conversion,
                        "maximum_temperature_K": tmax, "outlet_temperature_K": tout,
                        "reaction_rate_field": reaction_field, "peak_reaction_rate": reaction_peak,
                        "heat_release_field": heat_field, "peak_heat_release": heat_peak,
                        "max_species_sum_error": float(np.max(np.abs(sums - 1))), "carbon_balance_relative_error": carbon_error,
                        "mass_flow_rate_kg_s_per_m": mdot, "inlet_total_enthalpy_J_kg": float(bulk_h["reactant-inlet"]),
                        "outlet_total_enthalpy_J_kg": float(bulk_h["outlet"]), "total_enthalpy_flux_drop_W_per_m": total_enthalpy_flux_drop,
                        "wall_heat_out_W_per_m": wall_heat, "global_total_enthalpy_balance_relative_error": energy_error},
                        "checks": checks, "files": [str(mesh.resolve()), str(raw.resolve()), str((OUT / 'case_f.cas.h5').resolve())],
                        "status": "PASS" if all(checks.values()) else "FAIL"})
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_f.json", payload); print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
