"""Case G: Fluent-native premixed methane/air autoignition in an adiabatic channel."""

from __future__ import annotations

import numpy as np

from fluent_mesh import write_fluent_ascii
from fluent_smoke_common import fluent_session, read_fluent_ascii_export
from phase_reactive_common import OUT, base_payload, ensure_dirs, write_json


CASE = "G"
L, H, U, TIN = 0.04, 0.004, 0.25, 900.0
YCH4, YO2 = 0.055, 0.220
IGNITION_T = 1400.0


def make_segmented_mesh(path):
    nx, ny = 40, 4
    xs = [L * i / nx for i in range(nx + 1)]
    ys = [H * j / ny for j in range(ny + 1)]
    points = [(x, y) for y in ys for x in xs]
    node = lambda i, j: j * len(xs) + i
    cells = [(node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1))
             for j in range(ny) for i in range(nx)]

    def boundary(_nodes, centroid):
        x, y = centroid
        if abs(x) < 1e-12:
            return "premixed-inlet", "velocity-inlet"
        if abs(x - L) < 1e-12:
            return "outlet", "pressure-outlet"
        if abs(y) < 1e-12 and 0.006 <= x <= 0.010:
            return "ignition-wall", "wall"
        if abs(y) < 1e-12:
            return "bottom-wall", "wall"
        return "top-wall", "wall"

    return write_fluent_ascii(path, dimension=2, points=points, cells=cells, boundary_name=boundary)


def species_field(allowed: list[str], name: str) -> str:
    if name in allowed:
        return name
    found = [v for v in allowed if name in v.lower() and ("mass" in v.lower() or "fraction" in v.lower())]
    if not found:
        raise RuntimeError(f"No field for {name}")
    return found[0]


def main() -> int:
    ensure_dirs()
    mesh = OUT / "case_g_premixed.msh"
    stats = make_segmented_mesh(mesh)
    payload = base_payload(CASE, "Premixed methane-air autoignition and finite-rate flame zone", "Ansys Fluent Student 2026 R1")
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
            inlet = s.settings.setup.boundary_conditions.velocity_inlet["premixed-inlet"]
            inlet.momentum.velocity_magnitude.value = U
            inlet.thermal.temperature.value = TIN
            for name, value in {"ch4": YCH4, "o2": YO2, "co2": 0.0, "h2o": 0.0}.items():
                inlet.species.species_mass_fraction[name].value = value
            for name in ("bottom-wall", "top-wall"):
                wall = s.settings.setup.boundary_conditions.wall[name]
                wall.thermal.thermal_condition = "Heat Flux"
                wall.thermal.heat_flux.value = 0.0
            ignition = s.settings.setup.boundary_conditions.wall["ignition-wall"]
            ignition.thermal.thermal_condition = "Temperature"
            ignition.thermal.temperature.value = IGNITION_T
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.run_calculation.parameters.time_step_size = 0.001
            for _ in range(500):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
            allowed = list(s.fields.field_data.scalar_fields.allowed_values())
            fields = {name: species_field(allowed, name) for name in ("ch4", "o2", "co2", "h2o", "n2")}
            reaction_field = next((v for v in allowed if "reaction" in v.lower() and "rate" in v.lower()), None)
            quantities = ["x-coordinate", "y-coordinate", "temperature", "x-velocity", "y-velocity", "pressure", *fields.values()]
            if reaction_field:
                quantities.append(reaction_field)
            raw = OUT / "case_g_final.csv"
            s.settings.file.export.ascii(file_name=str(raw), surface_name_list=["interior", "premixed-inlet", "outlet"],
                                         delimiter="comma", quantities=quantities, location="node")
            s.settings.file.write_case_data(file_name=str(OUT / "case_g.cas.h5"))
        rows = list({(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in read_fluent_ascii_export(raw)}.values())
        outlet = [r for r in rows if abs(r["x-coordinate"] - L) < 1e-9]
        yout = {name: float(np.mean([r[field] for r in outlet])) for name, field in fields.items()}
        rates = np.asarray([abs(r[reaction_field]) for r in rows]) if reaction_field else np.zeros(len(rows))
        internal_ids = [idx for idx, r in enumerate(rows) if 0.05 * L < r["x-coordinate"] < 0.95 * L]
        if not internal_ids:
            raise RuntimeError("No interior reaction-rate samples")
        peak_index = max(internal_ids, key=lambda idx: rates[idx])
        peak = rows[peak_index]
        temperatures = np.asarray([r["temperature"] for r in rows])
        sums = np.asarray([sum(r[f] for f in fields.values()) for r in rows])
        conversion = 1.0 - yout["ch4"] / YCH4
        carbon_in = YCH4 * 12.011 / 16.04303
        carbon_out = yout["ch4"] * 12.011 / 16.04303 + yout["co2"] * 12.011 / 44.00995
        carbon_error = abs(carbon_out - carbon_in) / carbon_in
        checks = {
            "native_finite_rate_combustion": reaction_field is not None and float(np.max(rates)) > 0,
            "substantial_fuel_conversion_gt_20pct": conversion > 0.20,
            "exothermic_temperature_rise_gt_100K": float(np.max(temperatures)) > TIN + 100.0,
            "temperature_below_3000K_sanity_bound": float(np.max(temperatures)) < 3000.0,
            "reaction_zone_is_internal": 0.10 * L < peak["x-coordinate"] < 0.90 * L,
            "species_bounded": all(-1e-5 <= r[f] <= 1.0 + 1e-5 for r in rows for f in fields.values()),
            "species_sum_error_lt_1e-4": float(np.max(np.abs(sums - 1.0))) < 1e-4,
            "carbon_balance_lt_5pct": carbon_error < 0.05,
        }
        payload.update({
            "model": {"species_transport": True, "chemistry": "finite-rate", "mechanism": "Fluent methane-air one-step",
                      "configuration": "premixed channel with a short internal ignition wall", "inlet": {"Y_CH4": YCH4, "Y_O2": YO2,
                      "temperature_K": TIN, "velocity_m_s": U}, "time_integration": {"dt_s": 0.001, "steps": 500, "final_time_s": 0.5}},
            "diagnostic": {"targeted_retest": 2, "ignition_wall_temperature_K": IGNITION_T,
                           "ignition_wall_x_range_m": [0.006, 0.010],
                           "rationale": "retain the lower-enthalpy internal ignition setup and raise inlet velocity to prevent upstream flame migration; acceptance thresholds unchanged"},
            "mesh": stats,
            "results": {"outlet_mass_fractions": yout, "fuel_conversion": conversion,
                        "maximum_temperature_K": float(np.max(temperatures)), "outlet_temperature_K": float(np.mean([r["temperature"] for r in outlet])),
                        "reaction_rate_field": reaction_field, "peak_reaction_rate": float(np.max(rates)),
                        "reaction_peak_location_m": [peak["x-coordinate"], peak["y-coordinate"]],
                        "carbon_balance_relative_error": carbon_error, "max_species_sum_error": float(np.max(np.abs(sums - 1.0)))},
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
            "files": [str(p.resolve()) for p in (mesh, raw, OUT / "case_g.cas.h5")],
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_g.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
