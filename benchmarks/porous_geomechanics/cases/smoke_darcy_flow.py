"""Case A: Fluent one-dimensional Darcy-flow benchmark."""

from __future__ import annotations

from fluent_smoke_common import svg_xy_plot, write_csv
from porous_field_export import export_fluent_rows
from porous_geomechanics_common import *


CASE = "darcy_flow"
LENGTH, HEIGHT, RHO, MU, K, POROSITY, U = 1.0, 0.10, 1000.0, 1.0e-3, 1.0e-8, 0.35, 0.01


def main() -> int:
    paths = clean_case(CASE)
    try:
        solved = solve_porous_channel(CASE, U, viscous_resistance=(1/K, 1/K),
                                      length=LENGTH, height=HEIGHT, rho=RHO, mu=MU,
                                      porosity=POROSITY)
        expected_gradient = MU * U / K
        expected_drop = expected_gradient * 0.8 * LENGTH
        errors = {
            "pressure_gradient_relative": relative_error(solved["pressure_gradient_pa_m"], expected_gradient),
            "pressure_drop_relative": relative_error(solved["pressure_drop_pa"], expected_drop),
            "permeability_relative": relative_error(MU*U/solved["pressure_gradient_pa_m"], K),
        }
        checks = {"pressure_gradient_error_lt_3pct": errors["pressure_gradient_relative"] < .03,
                  "flow_rate_positive": solved["mass_flow_per_depth_kg_m_s"] > 0,
                  "permeability_error_lt_3pct": errors["permeability_relative"] < .03}
        line = sorted({r["x-coordinate"]: r for r in solved["field_rows"] if abs(r["y-coordinate"]-HEIGHT/2) < HEIGHT/12}.values(), key=lambda r:r["x-coordinate"])
        csv_path = write_csv(paths["dir"] / "darcy_pressure_profile.csv", ["x_m","pressure_pa"],
                             [{"x_m":r["x-coordinate"],"pressure_pa":r["pressure"]} for r in line])
        svg_path = svg_xy_plot(paths["dir"] / "darcy_pressure_profile.svg",
                               [(r["x-coordinate"],r["pressure"]) for r in line],
                               title="Case A: Darcy pressure field", xlabel="x (m)", ylabel="pressure (Pa)")
        npz = export_fluent_rows(paths["dir"] / "darcy_field.npz", solved["field_rows"], metadata={
            "case":"A", "solver":"Fluent 261", "model":"isotropic Darcy porous medium",
            "parameters":{"K_m2":K,"porosity":POROSITY,"mu_pa_s":MU,"rho_kg_m3":RHO},
            "units":{"coordinates":"m","pressure":"Pa","velocity":"m/s"}})
        payload = status_payload("A", "Darcy one-dimensional seepage", "PASS" if all(checks.values()) else "FAIL",
            solver="Ansys Fluent", material_model="isotropic porous resistance", permeability_m2=K,
            porosity=POROSITY, fluid={"density_kg_m3":RHO,"viscosity_pa_s":MU}, mesh=solved["mesh"],
            results={k:v for k,v in solved.items() if k not in ("field_rows","zone_state","files","mesh")},
            theory={"law":"dp/L=mu*U/K","pressure_gradient_pa_m":expected_gradient,"pressure_drop_pa":expected_drop},
            errors=errors, checks=checks, files=solved["files"]+[str(csv_path.resolve()),str(svg_path.resolve()),str(npz.resolve())])
    except Exception as exc:
        status, error = classify_solver_error(exc)
        payload = status_payload("A", "Darcy one-dimensional seepage", status, error=error,
                                 files=[str(paths["input"].resolve())] if paths["input"].exists() else [])
    write_json(paths["result"], payload); print(payload)
    return 0 if payload["status"] in ("PASS", "BLOCKED BY CURRENT LICENSE CONTEXT") else 1


if __name__ == "__main__": raise SystemExit(main())
