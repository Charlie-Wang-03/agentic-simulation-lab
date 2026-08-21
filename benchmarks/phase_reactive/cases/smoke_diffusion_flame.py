"""Case H: Fluent-native non-premixed methane/air mixing and finite-rate reaction."""

from __future__ import annotations

import math
import numpy as np

from fluent_mesh import split_inlet_channel_2d
from fluent_smoke_common import fluent_session, read_fluent_ascii_export
from phase_reactive_common import OUT, base_payload, ensure_dirs, write_json


CASE = "H"
L, H, U, TIN = 0.020, 0.006, 0.10, 1000.0
FUEL_CH4 = 0.20


def species_field(allowed: list[str], name: str) -> str:
    if name in allowed:
        return name
    matches = [v for v in allowed if name in v.lower() and ("mass" in v.lower() or "fraction" in v.lower())]
    if not matches:
        raise RuntimeError(f"No exported field for species {name}")
    return matches[0]


def main() -> int:
    ensure_dirs()
    mesh = OUT / "case_h_diffusion_flame.msh"
    stats = split_inlet_channel_2d(mesh, length=L, height=H, nx=30, ny=8)
    payload = base_payload(CASE, "Finite-rate methane/air diffusion flame and mixing layer", "Ansys Fluent Student 2026 R1")
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
            compositions = {
                "inlet-upper": {"ch4": FUEL_CH4, "o2": 0.0, "co2": 0.0, "h2o": 0.0},
                "inlet-lower": {"ch4": 0.0, "o2": 0.23, "co2": 0.0, "h2o": 0.0},
            }
            for zone, comp in compositions.items():
                inlet = s.settings.setup.boundary_conditions.velocity_inlet[zone]
                inlet.momentum.velocity_magnitude.value = U
                inlet.thermal.temperature.value = TIN
                for species, value in comp.items():
                    inlet.species.species_mass_fraction[species].value = value
            wall = s.settings.setup.boundary_conditions.wall["channel-wall"]
            wall.thermal.thermal_condition = "Temperature"
            wall.thermal.temperature.value = TIN
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.run_calculation.parameters.time_step_size = 0.001
            for _ in range(400):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
            allowed = list(s.fields.field_data.scalar_fields.allowed_values())
            fields = {name: species_field(allowed, name) for name in ("ch4", "o2", "co2", "h2o", "n2")}
            reaction_field = next((v for v in allowed if "reaction" in v.lower() and "rate" in v.lower()), None)
            quantities = ["x-coordinate", "y-coordinate", "temperature", "x-velocity", "y-velocity", "pressure", *fields.values()]
            if reaction_field:
                quantities.append(reaction_field)
            raw = OUT / "case_h_final.csv"
            s.settings.file.export.ascii(
                file_name=str(raw), surface_name_list=["interior", "inlet-upper", "inlet-lower", "outlet"],
                delimiter="comma", quantities=quantities, location="node"
            )
            s.settings.file.write_case_data(file_name=str(OUT / "case_h.cas.h5"))
        rows = list({(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in read_fluent_ascii_export(raw)}.values())
        sums = np.asarray([sum(r[f] for f in fields.values()) for r in rows])
        rates = np.asarray([abs(r[reaction_field]) for r in rows]) if reaction_field else np.zeros(len(rows))
        temperatures = np.asarray([r["temperature"] for r in rows])
        peak_index = int(np.argmax(rates))
        peak_row = rows[peak_index]
        active = rates > 0.10 * max(float(np.max(rates)), 1e-300)
        hot = temperatures > TIN + 0.10 * max(float(np.max(temperatures) - TIN), 1e-12)
        overlap = float(np.count_nonzero(active & hot) / max(np.count_nonzero(active), 1))
        mixing_at_peak = peak_row[fields["ch4"]] > 1e-6 and peak_row[fields["o2"]] > 1e-6
        checks = {
            "native_species_transport": True,
            "native_finite_rate_reaction": reaction_field is not None and float(np.max(rates)) > 0.0,
            "fuel_and_oxidizer_mix_at_reaction_peak": bool(mixing_at_peak),
            "temperature_rises_gt_10K": float(np.max(temperatures)) > TIN + 10.0,
            "reaction_hot_region_overlap_gt_50pct": overlap > 0.5,
            "species_bounded": all(-1e-5 <= r[f] <= 1.0 + 1e-5 for r in rows for f in fields.values()),
            "species_sum_error_lt_1e-4": float(np.max(np.abs(sums - 1.0))) < 1e-4,
        }
        payload.update({
            "model": {"species_transport": True, "chemistry": "finite-rate", "mechanism": "Fluent methane-air one-step",
                      "inlets": compositions, "temperature_K": TIN, "velocity_m_s": U,
                      "time_integration": {"dt_s": 0.001, "steps": 400, "final_time_s": 0.4}},
            "mesh": stats,
            "results": {"maximum_temperature_K": float(np.max(temperatures)), "reaction_rate_field": reaction_field,
                        "peak_reaction_rate": float(np.max(rates)), "reaction_peak_location_m": [peak_row["x-coordinate"], peak_row["y-coordinate"]],
                        "peak_Y_CH4": peak_row[fields["ch4"]], "peak_Y_O2": peak_row[fields["o2"]],
                        "reaction_hot_region_overlap": overlap, "max_species_sum_error": float(np.max(np.abs(sums - 1.0)))},
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
            "files": [str(p.resolve()) for p in (mesh, raw, OUT / "case_h.cas.h5")],
        })
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_h.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
