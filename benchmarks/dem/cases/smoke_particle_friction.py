"""Case C: static/dynamic particle-wall friction on an equivalent incline."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_c_friction"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
MU_STATIC = 0.5
MU_DYNAMIC = 0.4
result = {"case": "C", "status": "FAIL", "stage": "initializing"}


def run_angle(angle_deg):
    label = f"angle_{angle_deg:g}deg"
    subdir = OUTPUT_DIR / label
    subdir.mkdir(parents=True, exist_ok=True)
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName(f"Case C - Equivalent Incline {angle_deg:g} deg")
    project_path = subdir / f"{label}.rocky"
    project.SaveProject(str(project_path))

    materials = study.GetMaterialCollection()
    particle_material = materials.GetDefaultParticleMaterial()
    wall_material = materials.GetDefaultBoundaryMaterial()
    particle_material.SetDensity(2500.0, "kg/m3")
    particle_material.SetYoungsModulus(1.0e6, "Pa")
    wall_material.SetYoungsModulus(1.0e7, "Pa")
    interaction = materials.GetMaterialsInteractionCollection().GetMaterialsInteraction(
        particle_material, wall_material
    )
    interaction.SetRestitutionCoefficient(0.1)
    interaction.SetStaticFriction(MU_STATIC)
    interaction.SetDynamicFriction(MU_DYNAMIC)

    particle = study.CreateParticle()
    particle.SetName("Non-Rotating Friction Sphere")
    particle.SetEnableRotations(False)
    particle.SetMaterial(particle_material)
    particle.GetSizeDistributionList()[0].SetSize(0.01, "m")
    wall = study.ImportWall(str(ROOT / "assets" / "rocky" / "floor.stl"))[0]
    wall.SetMaterial(wall_material)

    release = study.CreateCircularSurface()
    release.SetCenter((-0.05, 0.0, 0.008), "m")
    release.SetMaxRadius(0.02, "m")
    release.SetOrientationFromBasisVector(
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    )
    inlet = study.CreateParticleInlet(release, particle)
    inlet.SetInjectionDuration(0.02, "s")
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(0.1, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.001, "kg/s")

    theta = math.radians(angle_deg)
    physics = study.GetPhysics()
    physics.SetGravityXDirection(9.81 * math.sin(theta), "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81 * math.cos(theta), "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.1, -0.05, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((0.5, 0.05, 0.05), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(0.30, "s")
    solver.SetTimeInterval(0.005, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    table_path = subdir / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = list(csv.DictReader(table_path.open(encoding="utf-8")))
    series = [
        (float(row["time_s"]), float(row["velocity_x_m_per_s"]))
        for row in rows
        if row.get("particle_id") and row.get("velocity_x_m_per_s")
    ]
    late = [(time, velocity) for time, velocity in series if time >= 0.15]
    if len(late) >= 2:
        mean_t = sum(item[0] for item in late) / len(late)
        mean_v = sum(item[1] for item in late) / len(late)
        denom = sum((item[0] - mean_t) ** 2 for item in late)
        acceleration = (
            sum((item[0] - mean_t) * (item[1] - mean_v) for item in late) / denom
            if denom
            else math.nan
        )
    else:
        acceleration = math.nan
    final_velocity = series[-1][1] if series else math.nan
    project.CloseProject(check_save_state=False)
    return {
        "angle_deg": angle_deg,
        "tan_angle": math.tan(theta),
        "simulation_result": simulation_result,
        "particle_rows": metadata["row_count"],
        "final_velocity_x_m_per_s": final_velocity,
        "fitted_acceleration_x_m_per_s2": acceleration,
        "expected_sliding_acceleration_m_per_s2": 9.81
        * (math.sin(theta) - MU_DYNAMIC * math.cos(theta)),
        "project": str(project_path),
        "particle_table": str(table_path),
    }


try:
    below = run_angle(20.0)
    above = run_angle(35.0)
    below_holds = abs(below["final_velocity_x_m_per_s"]) <= 0.03
    expected_acceleration = above["expected_sliding_acceleration_m_per_s2"]
    acceleration_error = abs(above["fitted_acceleration_x_m_per_s2"] - expected_acceleration)
    above_slides = (
        above["final_velocity_x_m_per_s"] > 0.1
        and acceleration_error <= max(0.6, 0.25 * expected_acceleration)
    )
    passed = (
        below["simulation_result"]
        and above["simulation_result"]
        and below["particle_rows"] > 0
        and above["particle_rows"] > 0
        and below_holds
        and above_slides
    )
    result.update(
        {
            "status": "PASS" if passed else "FAIL",
            "stage": "validation",
            "mu_static": MU_STATIC,
            "mu_dynamic": MU_DYNAMIC,
            "critical_angle_deg": math.degrees(math.atan(MU_STATIC)),
            "below_critical": below,
            "above_critical": above,
            "below_holds": below_holds,
            "above_slides": above_slides,
            "above_acceleration_absolute_error_m_per_s2": acceleration_error,
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
