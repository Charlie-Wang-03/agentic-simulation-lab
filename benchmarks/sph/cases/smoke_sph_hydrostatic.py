"""Case A: native SPH hydrostatic pressure benchmark in an open tank."""

from pathlib import Path
import json
import math
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, read_sph_steps


OUT = OUTPUT_ROOT / "case_a_hydrostatic"
OUT.mkdir(parents=True, exist_ok=True)
RESULT = OUT / "result.json"
result = {"case": "A", "status": "FAIL", "stage": "initializing"}
try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case A - SPH Hydrostatics")
    project_path = OUT / "case_a_hydrostatic.rocky"
    project.SaveProject(str(project_path))
    sph, water, physics = configure_water_sph(study, size_m=0.01, solver_model="IISPH")
    tank, boundary_values = import_open_tank(study, asset="sph_hydro_tank.stl")
    add_sph_volume(
        study, name="Hydrostatic Water", center_m=(0.0, 0.0, 0.035),
        dimensions_m=(0.06, 0.04, 0.06), sph_size_m=0.01,
    )
    set_domain(study)
    result["stage"] = "simulation"
    simulation_ok = solve(study, project, project_path, duration_s=0.50, output_dt_s=0.05)
    result["stage"] = "validation"
    metadata = export_lagrangian(study, OUT / "sph_lagrangian.csv")
    steps, _ = read_sph_steps(study)
    final = steps[-1][1] if steps else []
    surface = max((float(row["position_z_m"]) for row in final), default=math.nan) + 0.005
    comparisons = []
    for row in final:
        z = float(row["position_z_m"])
        measured = float(row["pressure_pa"])
        expected = WATER_DENSITY * GRAVITY * max(0.0, surface - z)
        if z < surface - 0.003:
            comparisons.append({"z_m": z, "depth_m": surface-z, "pressure_pa": measured, "expected_pa": expected})
    # SPH point pressure is intentionally noisy. Hydrostatic validation uses
    # horizontal layer means (half-element bins), which is the resolved field
    # quantity corresponding to p=rho*g*h rather than a single kernel sample.
    layers = {}
    for item in comparisons:
        key = round(item["z_m"] / 0.005) * 0.005
        layers.setdefault(key, []).append(item["pressure_pa"])
    layer_comparison = [
        {"z_m": z, "depth_m": surface-z, "mean_pressure_pa": sum(values)/len(values),
         "expected_pa": WATER_DENSITY*GRAVITY*max(0.0, surface-z), "element_count": len(values)}
        for z, values in sorted(layers.items())
    ]
    rmse = math.sqrt(sum((x["mean_pressure_pa"]-x["expected_pa"])**2 for x in layer_comparison)/len(layer_comparison)) if layer_comparison else math.inf
    scale = max((x["expected_pa"] for x in layer_comparison), default=0.0)
    speeds = [math.sqrt(float(r["velocity_x_m_per_s"])**2+float(r["velocity_y_m_per_s"])**2+float(r["velocity_z_m_per_s"])**2) for r in final]
    mean_speed = sum(speeds)/len(speeds) if speeds else math.inf
    masses = [sum(float(row["mass_kg"]) for row in rows) for _, rows in steps]
    mass_drift = (max(masses)-min(masses))/max(masses[0], 1e-30) if masses else math.inf
    densities = [float(row["density_kg_per_m3"]) for row in final]
    density_dev = max((abs(x-WATER_DENSITY)/WATER_DENSITY for x in densities), default=math.inf)
    checks = {
        "solver_advanced": simulation_ok,
        "at_least_20_elements": len(final) >= 20,
        "mass_conservation_lt_1pct": mass_drift < 0.01,
        "density_deviation_lt_5pct": density_dev < 0.05,
        "hydrostatic_rmse_lt_50pct_head": rmse/max(scale,1.0) < 0.50,
        "mean_speed_lt_0p1_m_per_s": mean_speed < 0.10,
        "finite_fields": all(finite([row["position_x_m"],row["position_z_m"],row["velocity_z_m_per_s"],row["pressure_pa"],row["density_kg_per_m3"]]) for row in final),
    }
    result.update({
        "status":"PASS" if all(checks.values()) else "FAIL", "checks":checks,
        "element_size_m":0.01, "element_count":len(final), "free_surface_height_m":surface,
        "pressure_rmse_pa":rmse, "pressure_rmse_fraction_of_head":rmse/max(scale,1.0),
        "mean_speed_m_per_s":mean_speed,
        "relative_mass_drift":mass_drift, "maximum_relative_density_deviation":density_dev,
        "boundary_type_values":boundary_values, "metadata":metadata,
        "pressure_comparison":comparisons, "layer_pressure_comparison":layer_comparison,
        "project":str(project_path),
    })
except Exception:
    result["error"] = traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try: app.Exit()
    except Exception: pass
