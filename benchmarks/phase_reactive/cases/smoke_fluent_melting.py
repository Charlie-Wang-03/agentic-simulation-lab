"""Case B: transient Fluent enthalpy-porosity melting in a 2-D PCM slab."""

from __future__ import annotations

import json
import math
import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import fluent_session, read_fluent_ascii_export, tui
from phase_reactive_common import OUT, base_payload, ensure_dirs, relative_error, write_json


CASE = "B"
LENGTH, HEIGHT = 0.08, 0.01
RHO, CP, K, MU, LATENT = 780.0, 2200.0, 0.20, 0.05, 180_000.0
TS, TL, T0, TH = 300.0, 301.0, 295.0, 340.0


def _liquid_field(session) -> str:
    allowed = list(session.fields.field_data.scalar_fields.allowed_values())
    candidates = [x for x in allowed if "liquid" in x.lower() and "fraction" in x.lower()]
    if not candidates:
        raise RuntimeError(f"No liquid-fraction field; relevant fields={[x for x in allowed if 'solid' in x.lower() or 'melt' in x.lower() or 'enthal' in x.lower()]}")
    return candidates[0]


def main() -> int:
    ensure_dirs()
    mesh = OUT / "case_b_pcm.msh"
    xs = [LENGTH * i / 80 for i in range(81)]
    ys = [HEIGHT * j / 10 for j in range(11)]
    stats = rectangular_2d(mesh, xs, ys, left=("hot-wall", "wall"), right=("adiabatic-right", "wall"),
                           bottom=("adiabatic-bottom", "wall"), top=("adiabatic-top", "wall"))
    payload = base_payload(CASE, "Fluent Solidification & Melting PCM slab", "Ansys Fluent Student 2026 R1")
    snapshots, avg_fraction, input_energy, stored_energy = [], [], [], []
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh))
            s.settings.setup.general.solver.time = "unsteady-1st-order"
            s.settings.setup.models.viscous.model = "laminar"
            s.settings.setup.models.energy.enabled = True
            response = tui(s, "/define/models/solidification-melting yes")
            pcm = s.settings.setup.materials.fluid["air"]
            pcm.density.value = RHO; pcm.viscosity.value = MU
            pcm.specific_heat.value = CP; pcm.thermal_conductivity.value = K
            pcm.melting_heat.value = LATENT; pcm.tsolidus.value = TS; pcm.tliqidus.value = TL
            hot = s.settings.setup.boundary_conditions.wall["hot-wall"]
            hot.thermal.thermal_condition = "Temperature"; hot.thermal.temperature.value = TH
            for name in ("adiabatic-right", "adiabatic-bottom", "adiabatic-top"):
                wall = s.settings.setup.boundary_conditions.wall[name]
                wall.thermal.thermal_condition = "Heat Flux"; wall.thermal.heat_flux.value = 0.0
            s.settings.solution.run_calculation.parameters.time_step_size = 30.0
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.initialization.patch.calculate_patch(cell_zones=["fluid"], variable="temperature", value=T0)
            lf = _liquid_field(s)
            allowed = list(s.fields.field_data.scalar_fields.allowed_values())
            hfield = next((x for x in allowed if "enthalpy" in x.lower() and "total" in x.lower()), None)
            qfield = next((x for x in ("wall-heat-flux", "surface-heat-flux", "heat-flux") if x in allowed), None)
            for step in range(1, 121):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
                if step in (1, 10, 30, 60, 120):
                    raw = OUT / f"case_b_t{step*30:05d}.csv"
                    quantities = ["x-coordinate", "y-coordinate", "temperature", lf]
                    if hfield: quantities.append(hfield)
                    if qfield: quantities.append(qfield)
                    s.settings.file.export.ascii(file_name=str(raw),
                        surface_name_list=["interior", "hot-wall", "adiabatic-right", "adiabatic-bottom", "adiabatic-top"],
                        delimiter="comma", quantities=quantities, location="node")
                    rows = read_fluent_ascii_export(raw)
                    unique = {(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in rows}
                    interior = list(unique.values())
                    fbar = float(np.mean([r[lf] for r in interior]))
                    avg_fraction.append(fbar); snapshots.append(step * 30.0)
                    # Per-unit-depth enthalpy increase from nodal mean; sufficient for the smoke balance.
                    temp = np.asarray([r["temperature"] for r in interior]); frac = np.asarray([r[lf] for r in interior])
                    stored = RHO * LENGTH * HEIGHT * (CP * float(np.mean(temp - T0)) + LATENT * fbar)
                    stored_energy.append(stored)
                    if qfield:
                        hot_rows = [r for r in rows if abs(r["x-coordinate"]) < 1e-10 and qfield in r]
                        q = float(np.mean([abs(r[qfield]) for r in hot_rows])) if hot_rows else math.nan
                    else: q = math.nan
                    input_energy.append(q)
            s.settings.file.write_case_data(file_name=str(OUT / "case_b.cas.h5"))
        # Compare the enthalpy gain between the first and last saved states with
        # the hot-wall input integrated over the same interval.  The five-point
        # quadrature is intentionally sparse, so this is a smoke-level balance.
        sampled_input = float(np.trapezoid(np.asarray(input_energy) * HEIGHT, np.asarray(snapshots)))
        sampled_stored_gain = stored_energy[-1] - stored_energy[0]
        sampled_energy_error = relative_error(sampled_stored_gain, sampled_input)
        max_drop = float(max(0.0, -np.min(np.diff(avg_fraction)))) if len(avg_fraction) > 1 else 0.0
        checks = {"native_model_enabled": bool(response), "multiple_snapshots": len(snapshots) == 5,
                  "liquid_fraction_bounded": all(-1e-6 <= x <= 1 + 1e-6 for x in avg_fraction),
                  "melting_progresses": avg_fraction[-1] > avg_fraction[0] + 0.05,
                  "melt_fraction_nearly_monotonic": max_drop < 0.01,
                  "stored_energy_positive": stored_energy[-1] > 0,
                  "sparse_wall_flux_energy_balance_lt_20pct": sampled_energy_error < 0.20}
        payload.update({"model": {"energy": True, "solidification_melting": True,
                        "formulation": "enthalpy-porosity", "mushy_zone_parameter": "Fluent default",
                        "material": {"rho_kg_m3": RHO, "cp_J_kgK": CP, "k_W_mK": K,
                                     "mu_Pa_s": MU, "latent_heat_J_kg": LATENT,
                                     "solidus_K": TS, "liquidus_K": TL}},
                        "mesh": stats, "time": {"dt_s": 30.0, "steps": 120, "snapshots_s": snapshots},
                        "results": {"average_liquid_fraction": avg_fraction,
                                    "stored_enthalpy_increase_J_per_m_depth": stored_energy,
                                    "sampled_hot_wall_heat_flux_W_m2": input_energy,
                                    "sampled_input_energy_30_to_3600s_J_per_m_depth": sampled_input,
                                    "stored_enthalpy_gain_30_to_3600s_J_per_m_depth": sampled_stored_gain,
                                    "sparse_energy_balance_relative_error": sampled_energy_error,
                                    "energy_balance_qualification": "five saved wall-flux samples; trapezoidal integration over 30-3600 s"},
                        "checks": checks, "files": [str(mesh.resolve()), str((OUT / 'case_b.cas.h5').resolve())],
                        "status": "PASS" if all(checks.values()) else "FAIL"})
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_b.json", payload); print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
