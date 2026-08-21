"""Case G: sphere versus Rocky-native sphero-cylinder impact/rotation."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_g_nonspherical"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "G", "status": "FAIL", "stage": "initializing"}


def run_shape(shape):
    subdir = OUTPUT_DIR / shape
    subdir.mkdir(parents=True, exist_ok=True)
    project = app.CreateProject()
    study = project.GetStudy()
    project_path = subdir / f"{shape}.rocky"
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
    interaction.SetRestitutionCoefficient(0.15)
    interaction.SetStaticFriction(0.6)
    interaction.SetDynamicFriction(0.5)

    particle = study.CreateParticle()
    valid_shapes = list(particle.GetValidShapeValues())
    particle.SetShape(shape)
    if shape == "sphero_cylinder":
        particle.SetVerticalAspectRatio(2.0)
    particle.SetMaterial(particle_material)
    particle.GetSizeDistributionList()[0].SetSize(0.01, "m")
    wall = study.ImportWall(str(ROOT / "assets" / "rocky" / "floor.stl"))[0]
    wall.SetMaterial(wall_material)
    release = study.CreateCircularSurface()
    release.SetCenter((-0.02, 0.0, 0.03), "m")
    release.SetMaxRadius(0.02, "m")
    release.SetOrientationFromBasisVector(
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    )
    inlet = study.CreateParticleInlet(release, particle)
    inlet.SetInjectionDuration(0.02, "s")
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(0.5, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.001, "kg/s")
    physics = study.GetPhysics()
    physics.SetGravityXDirection(3.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.1, -0.05, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((0.2, 0.05, 0.08), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(0.20, "s")
    solver.SetTimeInterval(0.005, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))
    table_path = subdir / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = [
        row
        for row in csv.DictReader(table_path.open(encoding="utf-8"))
        if row.get("particle_id")
    ]
    final = rows[-1] if rows else {}
    angular_speed = math.sqrt(
        sum(
            float(final.get(name) or 0.0) ** 2
            for name in (
                "angular_velocity_x_rad_per_s",
                "angular_velocity_y_rad_per_s",
                "angular_velocity_z_rad_per_s",
            )
        )
    )
    orientation = {
        name: float(final[name])
        for name in (
            "orientation_angle_rad",
            "orientation_axis_x",
            "orientation_axis_y",
            "orientation_axis_z",
        )
        if final.get(name)
    }
    project.CloseProject(check_save_state=False)
    return {
        "shape": shape,
        "valid_shape_values": valid_shapes,
        "simulation_result": simulation_result,
        "particle_rows": metadata["row_count"],
        "final_angular_speed_rad_per_s": angular_speed,
        "final_orientation": orientation,
        "project": str(project_path),
        "particle_table": str(table_path),
    }


try:
    spherical = run_shape("sphere")
    nonspherical = run_shape("sphero_cylinder")
    orientation_complete = len(nonspherical["final_orientation"]) == 4
    rotation_difference = abs(
        nonspherical["final_angular_speed_rad_per_s"]
        - spherical["final_angular_speed_rad_per_s"]
    )
    passed = (
        spherical["simulation_result"]
        and nonspherical["simulation_result"]
        and spherical["particle_rows"] > 0
        and nonspherical["particle_rows"] > 0
        and orientation_complete
        and rotation_difference > 1.0e-4
    )
    result.update(
        {
            "status": "PASS" if passed else "FAIL",
            "stage": "validation",
            "spherical": spherical,
            "nonspherical": nonspherical,
            "orientation_complete": orientation_complete,
            "angular_speed_difference_rad_per_s": rotation_difference,
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
