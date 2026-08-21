"""Case I: controlled no-radiation/P-1 comparison from the same reacting field."""

from __future__ import annotations

import json
import numpy as np

from fluent_smoke_common import fluent_session, read_fluent_ascii_export
from phase_reactive_common import OUT, base_payload, ensure_dirs, write_json


CASE = "I"
TIN = 1200.0


def run_branch(s, *, radiation: bool):
    s.settings.file.read_case_data(file_name=str(OUT / "case_g.cas.h5"))
    for name in ("bottom-wall", "top-wall"):
        wall = s.settings.setup.boundary_conditions.wall[name]
        wall.thermal.thermal_condition = "Temperature"
        wall.thermal.temperature.value = TIN
    if radiation:
        s.settings.setup.models.radiation.model = "p1"
        s.settings.setup.materials.mixture["methane-air"].absorption_coefficient.value = 20.0
    else:
        s.settings.setup.models.radiation.model = "none"
    s.settings.solution.run_calculation.parameters.time_step_size = 0.001
    for _ in range(100):
        s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
    allowed = list(s.fields.field_data.scalar_fields.allowed_values())
    rad_fields = [v for v in ("incident-radiation", "radiation-temperature", "volumetric-absorbed-radiation", "volumetric-emitted-radiation") if v in allowed]
    raw = OUT / ("case_i_p1.csv" if radiation else "case_i_no_radiation.csv")
    quantities = ["x-coordinate", "y-coordinate", "temperature", "ch4", "o2", "co2", "h2o", "n2"]
    if radiation:
        quantities += rad_fields
    s.settings.file.export.ascii(file_name=str(raw), surface_name_list=["interior", "outlet"], delimiter="comma",
                                 quantities=quantities, location="node")
    integrals = s.settings.results.report.surface_integrals
    flows = integrals.get_mass_flow_rate(surface_names=["premixed-inlet", "outlet"])
    enthalpy = integrals.get_mass_weighted_avg(surface_names=["premixed-inlet", "outlet"], report_of="total-enthalpy")
    wall_heat = abs(float(integrals.get_integral(surface_names=["bottom-wall", "top-wall"], report_of="heat-flux")["Net"]))
    mdot_in, mdot_out = abs(float(flows["premixed-inlet"])), abs(float(flows["outlet"]))
    enthalpy_flux_difference = abs(mdot_in * float(enthalpy["premixed-inlet"]) - mdot_out * float(enthalpy["outlet"]))
    energy_error = abs(enthalpy_flux_difference - wall_heat) / max(wall_heat, 1e-30)
    mass_error = abs(mdot_in - mdot_out) / max(0.5 * (mdot_in + mdot_out), 1e-30)
    if radiation:
        s.settings.file.write_case_data(file_name=str(OUT / "case_i_p1.cas.h5"))
    rows = list({(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in read_fluent_ascii_export(raw)}.values())
    t = np.asarray([r["temperature"] for r in rows])
    rad_max = {f: float(np.max(np.abs([r[f] for r in rows]))) for f in rad_fields if f in rows[0]}
    return {"maximum_temperature_K": float(np.max(t)), "mean_temperature_K": float(np.mean(t)),
            "minimum_temperature_K": float(np.min(t)), "radiation_fields": rad_fields, "radiation_field_abs_max": rad_max,
            "mass_flow_imbalance_relative": mass_error, "wall_heat_out_W_per_m": wall_heat,
            "total_enthalpy_flux_difference_W_per_m": enthalpy_flux_difference,
            "global_energy_balance_relative_error": energy_error,
            "energy_balance_qualification": "instantaneous coarse-transient balance; includes formation enthalpy and isothermal-wall total heat flux",
            "raw": str(raw.resolve())}


def main() -> int:
    ensure_dirs()
    payload = base_payload(CASE, "P-1 radiation coupling in finite-rate methane combustion", "Ansys Fluent Student 2026 R1")
    try:
        baseline_case = json.loads((OUT / "case_g.json").read_text(encoding="utf-8"))
        with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
            no_rad = run_branch(s, radiation=False)
            p1 = run_branch(s, radiation=True)
        delta_max = p1["maximum_temperature_K"] - no_rad["maximum_temperature_K"]
        delta_mean = p1["mean_temperature_K"] - no_rad["mean_temperature_K"]
        nonzero = any(v > 0 for v in p1["radiation_field_abs_max"].values())
        checks = {
            "same_reacting_initial_state": True,
            "p1_model_enabled": "incident-radiation" in p1["radiation_fields"],
            "radiation_field_nonzero": nonzero,
            "temperature_field_changes": abs(delta_max) > 0.1 or abs(delta_mean) > 0.1,
            "temperatures_finite_and_positive": all(np.isfinite(v) and v > 0 for v in (no_rad["minimum_temperature_K"], p1["minimum_temperature_K"])),
            "p1_mass_imbalance_lt_2pct": p1["mass_flow_imbalance_relative"] < 0.02,
            "p1_coarse_global_energy_balance_lt_30pct": p1["global_energy_balance_relative_error"] < 0.30,
        }
        payload.update({
            "model": {"radiation": "P-1", "absorption_coefficient_1_m": 20.0,
                      "comparison": "100 equal transient steps from identical case-G state with 1200 K walls",
                      "combustion_mechanism": "Fluent methane-air one-step finite-rate"},
            "source_case_g_status": baseline_case.get("status"),
            "results": {"no_radiation": no_rad, "p1": p1, "delta_max_temperature_K": delta_max, "delta_mean_temperature_K": delta_mean},
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
            "files": [no_rad["raw"], p1["raw"], str((OUT / "case_i_p1.cas.h5").resolve())],
            "qualification": "Radiation coupling is assessed independently; the inherited case-G premixed flame plausibility failure is not erased.",
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_i.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
