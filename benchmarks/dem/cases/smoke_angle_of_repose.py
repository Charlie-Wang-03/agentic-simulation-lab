"""Case D: many-particle pile and angle-of-repose friction trend."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_d_angle_of_repose"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "D", "status": "FAIL", "stage": "initializing"}


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return math.nan
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def run_friction(mu):
    label = f"mu_{mu:.2f}".replace(".", "p")
    subdir = OUTPUT_DIR / label
    subdir.mkdir(parents=True, exist_ok=True)
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName(f"Case D - Angle of Repose mu={mu:.2f}")
    project_path = subdir / f"{label}.rocky"
    project.SaveProject(str(project_path))

    materials = study.GetMaterialCollection()
    particle_material = materials.GetDefaultParticleMaterial()
    wall_material = materials.GetDefaultBoundaryMaterial()
    particle_material.SetDensity(2500.0, "kg/m3")
    particle_material.SetYoungsModulus(2.0e6, "Pa")
    wall_material.SetYoungsModulus(1.0e7, "Pa")
    interactions = materials.GetMaterialsInteractionCollection()
    for material_1, material_2 in (
        (particle_material, particle_material),
        (particle_material, wall_material),
    ):
        interaction = interactions.GetMaterialsInteraction(material_1, material_2)
        interaction.SetRestitutionCoefficient(0.25)
        interaction.SetStaticFriction(mu)
        interaction.SetDynamicFriction(0.8 * mu)

    particle = study.CreateParticle()
    particle.SetName("Pile Sphere")
    particle.SetMaterial(particle_material)
    physics = study.GetPhysics()
    rolling_models = list(physics.GetValidRollingResistanceModelValues())
    rolling_model = next(
        (value for value in rolling_models if value not in ("none", "None")),
        rolling_models[-1],
    )
    physics.SetRollingResistanceModel(rolling_model)
    particle.SetRollingResistance(0.30)
    particle.GetSizeDistributionList()[0].SetSize(0.005, "m")
    wall = study.ImportWall(str(ROOT / "assets" / "rocky" / "floor.stl"))[0]
    wall.SetMaterial(wall_material)

    inlet_surface = study.CreateCircularSurface()
    inlet_surface.SetCenter((0.0, 0.0, 0.12), "m")
    inlet_surface.SetMaxRadius(0.008, "m")
    inlet_surface.SetOrientationFromBasisVector(
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    )
    inlet = study.CreateParticleInlet(inlet_surface, particle)
    inlet.SetInjectionDuration(0.40, "s")
    inlet.DisablePeriodic()
    inlet.EnableForcePacking()
    inlet.SetStartTime(0.0, "s")
    inlet.SetStopTime(0.40, "s")
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(0.10, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.03, "kg/s")

    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.15, -0.15, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((0.15, 0.15, 0.18), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(2.00, "s")
    solver.SetTimeInterval(0.05, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    if study.GetTimeSet() is None:
        project.CloseProject(check_save_state=False)
        return {
            "friction_coefficient": mu,
            "simulation_result": simulation_result,
            "particle_count_final": 0,
            "pile_height_m_p95": math.nan,
            "pile_radius_m_p90": math.nan,
            "angle_of_repose_deg": math.nan,
            "mean_final_particle_speed_m_per_s": math.nan,
            "particle_rows": 0,
            "project": str(project_path),
            "error": "Rocky returned no result time set",
        }

    table_path = subdir / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = list(csv.DictReader(table_path.open(encoding="utf-8")))
    times = [float(row["time_s"]) for row in rows if row.get("particle_id")]
    final_time = max(times) if times else math.nan
    final_rows = [
        row
        for row in rows
        if row.get("particle_id") and abs(float(row["time_s"]) - final_time) < 1.0e-12
    ]
    xs = [float(row["position_x_m"]) for row in final_rows]
    ys = [float(row["position_y_m"]) for row in final_rows]
    zs = [float(row["position_z_m"]) for row in final_rows]
    center_x = sum(xs) / len(xs) if xs else 0.0
    center_y = sum(ys) / len(ys) if ys else 0.0
    radial = [math.hypot(x - center_x, y - center_y) for x, y in zip(xs, ys)]
    particle_radius = 0.0025
    pile_height = percentile(zs, 0.95) - particle_radius if zs else math.nan
    pile_radius = percentile(radial, 0.90) + particle_radius if radial else math.nan
    angle = math.degrees(math.atan2(max(pile_height, 0.0), pile_radius)) if pile_radius > 0 else math.nan
    speeds = [
        math.sqrt(
            float(row["velocity_x_m_per_s"]) ** 2
            + float(row["velocity_y_m_per_s"]) ** 2
            + float(row["velocity_z_m_per_s"]) ** 2
        )
        for row in final_rows
    ]
    mean_final_speed = sum(speeds) / len(speeds) if speeds else math.nan
    project.CloseProject(check_save_state=False)
    return {
        "friction_coefficient": mu,
        "rolling_resistance_model": rolling_model,
        "rolling_resistance": 0.30,
        "simulation_result": simulation_result,
        "particle_count_final": len(final_rows),
        "pile_height_m_p95": pile_height,
        "pile_radius_m_p90": pile_radius,
        "angle_of_repose_deg": angle,
        "mean_final_particle_speed_m_per_s": mean_final_speed,
        "particle_rows": metadata["row_count"],
        "project": str(project_path),
        "particle_table": str(table_path),
    }


try:
    low = run_friction(0.20)
    high = run_friction(0.60)
    trend_delta = high["angle_of_repose_deg"] - low["angle_of_repose_deg"]
    passed = (
        low["simulation_result"]
        and high["simulation_result"]
        and low["particle_count_final"] >= 20
        and high["particle_count_final"] >= 20
        and math.isfinite(trend_delta)
        and trend_delta >= 1.0
        and low["mean_final_particle_speed_m_per_s"] < 0.08
        and high["mean_final_particle_speed_m_per_s"] < 0.08
    )
    result.update(
        {
            "status": "PASS" if passed else "FAIL",
            "stage": "validation",
            "low_friction": low,
            "high_friction": high,
            "angle_trend_delta_deg": trend_delta,
            "trend_expected": "higher friction -> higher angle of repose",
        }
    )
except Exception:
    result["error"] = traceback.format_exc()
finally:
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        app.Exit()
    except Exception:
        pass
