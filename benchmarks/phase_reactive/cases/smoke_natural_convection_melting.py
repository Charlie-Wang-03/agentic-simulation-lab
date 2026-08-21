"""Case C: Fluent buoyancy-coupled melting versus zero-gravity reference."""

from __future__ import annotations

import math
import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import fluent_session, read_fluent_ascii_export, tui
from phase_reactive_common import OUT, base_payload, ensure_dirs, write_json


CASE = "C"
L = 0.04
RHO, CP, K, MU, BETA, LATENT = 780.0, 2200.0, 0.20, 0.30, 2.0e-3, 180_000.0
TS, TL, T0, TH = 300.0, 301.0, 295.0, 340.0


def _set_property(obj, names, value):
    for name in names:
        if name in getattr(obj, "child_names", []):
            child = getattr(obj, name)
            if "value" in getattr(child, "child_names", []): child.value = value
            else: child.set_state(value)
            return name
    raise RuntimeError(f"None of {names} in {getattr(obj, 'child_names', [])}")


def run_variant(mesh, name: str, gravity: bool) -> dict:
    raw = OUT / f"case_c_{name}_final.csv"
    with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
        s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.general.solver.time = "unsteady-1st-order"
        s.settings.setup.models.viscous.model = "laminar"; s.settings.setup.models.energy.enabled = True
        tui(s, "/define/models/solidification-melting yes")
        pcm = s.settings.setup.materials.fluid["air"]
        pcm.viscosity.value = MU; pcm.specific_heat.value = CP; pcm.thermal_conductivity.value = K
        pcm.melting_heat.value = LATENT; pcm.tsolidus.value = TS; pcm.tliqidus.value = TL
        if gravity:
            pcm.density.option = "boussinesq"
            _set_property(pcm.density, ["boussinesq_density", "reference_density", "rho0", "value"], RHO)
            _set_property(pcm, ["therm_exp_coeff", "thermal_expansion_coefficient"], BETA)
            grav = s.settings.setup.general.operating_conditions.gravity; grav.enable = True; grav.components = [0.0, -9.81, 0.0]
        else:
            pcm.density.value = RHO
        wall = s.settings.setup.boundary_conditions.wall["hot-wall"]
        wall.thermal.thermal_condition = "Temperature"; wall.thermal.temperature.value = TH
        for zone in ("cold-wall", "top-wall", "bottom-wall"):
            w = s.settings.setup.boundary_conditions.wall[zone]
            w.thermal.thermal_condition = "Heat Flux"; w.thermal.heat_flux.value = 0.0
        s.settings.solution.run_calculation.parameters.time_step_size = 1.0
        s.settings.solution.initialization.hybrid_initialize()
        s.settings.solution.initialization.patch.calculate_patch(cell_zones=["fluid"], variable="temperature", value=T0)
        allowed = list(s.fields.field_data.scalar_fields.allowed_values())
        lf = next(x for x in allowed if "liquid" in x.lower() and "fraction" in x.lower())
        for _ in range(100):
            s.settings.solution.run_calculation.dual_time_iterate(time_step_count=1, max_iter_per_step=20)
        s.settings.file.export.ascii(file_name=str(raw), surface_name_list=["interior", "hot-wall", "cold-wall", "top-wall", "bottom-wall"],
            delimiter="comma", quantities=["x-coordinate", "y-coordinate", "temperature", "x-velocity", "y-velocity", "velocity-magnitude", lf], location="node")
        s.settings.file.write_case_data(file_name=str(OUT / f"case_c_{name}.cas.h5"))
    rows = read_fluent_ascii_export(raw)
    unique = {(round(r["x-coordinate"], 12), round(r["y-coordinate"], 12)): r for r in rows}
    vals = list(unique.values()); fractions = np.asarray([r[lf] for r in vals])
    vmax = max(r["velocity-magnitude"] for r in vals)
    fronts = []
    for y in sorted({round(r["y-coordinate"], 10) for r in vals}):
        molten = [r["x-coordinate"] for r in vals if round(r["y-coordinate"], 10) == y and r[lf] >= 0.5]
        fronts.append(max(molten) if molten else 0.0)
    return {"name": name, "gravity": gravity, "average_liquid_fraction": float(np.mean(fractions)),
            "maximum_velocity_m_s": vmax, "front_mean_m": float(np.mean(fronts)),
            "front_std_m": float(np.std(fronts)), "liquid_fraction_range": [float(fractions.min()), float(fractions.max())],
            "raw": str(raw.resolve())}


def main() -> int:
    ensure_dirs(); mesh = OUT / "case_c_pcm_cavity.msh"
    coords = [L * i / 30 for i in range(31)]
    stats = rectangular_2d(mesh, coords, coords, left=("hot-wall", "wall"), right=("cold-wall", "wall"),
                           bottom=("bottom-wall", "wall"), top=("top-wall", "wall"))
    payload = base_payload(CASE, "Natural-convection-enhanced PCM melting", "Ansys Fluent Student 2026 R1")
    try:
        conduction = run_variant(mesh, "conduction", False)
        convection = run_variant(mesh, "buoyant", True)
        checks = {"both_native_runs_completed": True,
                  "fraction_bounded": all(-1e-6 <= v <= 1 + 1e-6 for r in (conduction, convection) for v in r["liquid_fraction_range"]),
                  "buoyant_flow_nonzero": convection["maximum_velocity_m_s"] > 1e-4,
                  "buoyant_velocity_stable": convection["maximum_velocity_m_s"] < 0.1,
                  "reference_flow_negligible": conduction["maximum_velocity_m_s"] < 1e-8,
                  "front_shape_changed": convection["front_std_m"] > conduction["front_std_m"] + 5e-4,
                  "overall_melting_changed": abs(convection["average_liquid_fraction"] - conduction["average_liquid_fraction"]) > 0.005}
        payload.update({"model": {"solidification_melting": True, "enthalpy_porosity": True,
                        "gravity_m_s2": [0, -9.81], "density": "Boussinesq", "beta_1_K": BETA},
                        "mesh": stats, "time": {"dt_s": 1.0, "steps": 100, "final_time_s": 100.0},
                        "reference": conduction, "results": convection, "checks": checks,
                        "files": [str(mesh.resolve()), conduction["raw"], convection["raw"]],
                        "status": "PASS" if all(checks.values()) else "FAIL"})
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / "case_c.json", payload); print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
