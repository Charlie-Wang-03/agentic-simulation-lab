"""Case A: 2-D fully developed laminar parallel-plate channel."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from fluent_mesh import rectangular_2d
from fluent_smoke_common import (
    OUT,
    base_payload,
    clean_case,
    fluent_session,
    read_fluent_ascii_export,
    rel_error,
    svg_xy_plot,
    write_csv,
    write_json,
)


CASE = "fluent_laminar_channel"
LENGTH = 0.50
HEIGHT = 0.010
U_MEAN = 0.10
RHO = 1.225
MU = 1.7894e-5


def clustered(a: float, b: float, intervals: int) -> list[float]:
    return [a + (b - a) * 0.5 * (1.0 - math.cos(math.pi * i / intervals)) for i in range(intervals + 1)]


def main() -> int:
    clean_case(CASE)
    mesh_path = OUT / f"{CASE}.msh"
    xs = [LENGTH * i / 160 for i in range(161)]
    ys = clustered(-HEIGHT / 2, HEIGHT / 2, 40)
    mesh_stats = rectangular_2d(mesh_path, xs, ys)
    payload = base_payload(CASE, "2-D steady incompressible laminar flow")
    payload["model"] = {"fluid": "air", "rho_kg_m3": RHO, "mu_pa_s": MU, "length_m": LENGTH, "height_m": HEIGHT, "inlet_velocity_m_s": U_MEAN}
    payload["mesh"] = {**mesh_stats, "type": "structured quadrilateral", "nx": 160, "ny": 40}
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh_path))
            s.settings.setup.models.viscous.model = "laminar"
            air = s.settings.setup.materials.fluid["air"]
            air.density.value = RHO
            air.viscosity.value = MU
            inlet = s.settings.setup.boundary_conditions.velocity_inlet["inlet"]
            inlet.momentum.velocity_magnitude.value = U_MEAN
            # Downstream profile and two pressure stations in the developed region.
            for name, x in (("profile", 0.45), ("pressure-upstream", 0.25), ("pressure-downstream", 0.45)):
                s.settings.results.surfaces.line_surface[name] = {
                    "p0": [x, -HEIGHT / 2, 0.0], "p1": [x, HEIGHT / 2, 0.0]
                }
            residuals = s.settings.solution.monitor.residual.equations
            for equation in ("continuity", "x_velocity", "y_velocity"):
                if hasattr(residuals, equation):
                    getattr(residuals, equation).absolute_criteria = 1.0e-7
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.run_calculation.iterate(iter_count=500)
            s.settings.file.write_case_data(file_name=str(OUT / f"{CASE}.cas.h5"))
            raw_export = OUT / f"{CASE}_raw.csv"
            s.settings.file.export.ascii(
                file_name=str(raw_export),
                surface_name_list=["profile", "pressure-upstream", "pressure-downstream"],
                delimiter="comma",
                quantities=["x-coordinate", "y-coordinate", "x-velocity", "pressure"],
                location="node",
            )

        raw_rows = read_fluent_ascii_export(raw_export)
        profile_rows = [r for r in raw_rows if abs(r["x-coordinate"] - 0.45) < 1e-8]
        up_rows = [r for r in raw_rows if abs(r["x-coordinate"] - 0.25) < 1e-8]
        if len(profile_rows) < 10 or len(up_rows) < 10:
            raise RuntimeError(f"Unexpected surface export counts: profile={len(profile_rows)}, upstream={len(up_rows)}")
        profile_rows.sort(key=lambda r: r["y-coordinate"])
        yvals = np.asarray([r["y-coordinate"] for r in profile_rows])
        uvals = np.asarray([r["x-velocity"] for r in profile_rows])
        p_up = float(np.mean([r["pressure"] for r in up_rows]))
        p_down = float(np.mean([r["pressure"] for r in profile_rows]))
        dp = p_up - p_down
        max_u = float(np.max(uvals))
        volume_flux = float(np.trapezoid(uvals, yvals))
        mass_flow = RHO * volume_flux

        theory_u = 1.5 * U_MEAN * (1.0 - (2.0 * yvals / HEIGHT) ** 2)
        theory_dp = 12.0 * MU * U_MEAN * (0.45 - 0.25) / HEIGHT**2
        theory_max = 1.5 * U_MEAN
        theory_mdot = RHO * U_MEAN * HEIGHT
        profile_l2 = float(np.linalg.norm(uvals - theory_u) / np.linalg.norm(theory_u))
        results = {
            "pressure_drop_0p25_to_0p45_pa": dp,
            "maximum_velocity_m_s": max_u,
            "mass_flow_per_depth_kg_m_s": mass_flow,
            "outlet_profile_mean_m_s": volume_flux / HEIGHT,
            "reynolds_height": RHO * U_MEAN * HEIGHT / MU,
        }
        theory = {"pressure_drop_pa": theory_dp, "maximum_velocity_m_s": theory_max, "mass_flow_per_depth_kg_m_s": theory_mdot, "profile": "u=1.5*Umean*(1-(2y/H)^2)"}
        errors = {"pressure_drop_relative": rel_error(dp, theory_dp), "maximum_velocity_relative": rel_error(max_u, theory_max), "mass_flow_relative": rel_error(mass_flow, theory_mdot), "profile_l2_relative": profile_l2}
        checks = {"pressure_drop_error_lt_8pct": errors["pressure_drop_relative"] < 0.08, "max_velocity_error_lt_3pct": errors["maximum_velocity_relative"] < 0.03, "mass_conservation_error_lt_1pct": errors["mass_flow_relative"] < 0.01, "profile_l2_error_lt_4pct": profile_l2 < 0.04}
        rows = [{"y_m": float(y), "fluent_u_m_s": float(u), "poiseuille_u_m_s": float(t)} for y, u, t in zip(yvals, uvals, theory_u)]
        csv_path = write_csv(OUT / f"{CASE}_velocity_profile.csv", list(rows[0]), rows)
        svg_path = svg_xy_plot(OUT / f"{CASE}_velocity_profile.svg", [(float(y), float(u)) for y, u in zip(yvals, uvals)], title="Case A: developed channel velocity profile", xlabel="y (m)", ylabel="u (m/s)", reference=[(float(y), float(t)) for y, t in zip(yvals, theory_u)])
        payload.update({"results": results, "theory": theory, "errors": errors, "checks": checks, "convergence": {"iterations_requested": 500, "fluent_stopped_when_converged": True, "residual_criteria": 1e-7}, "status": "PASS" if all(checks.values()) else "FAIL", "files": [str(p.resolve()) for p in (mesh_path, raw_export, csv_path, svg_path, OUT / f"{CASE}.cas.h5")]})
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
