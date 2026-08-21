"""Case B: one Rocky sphere impacts a rigid triangulated wall."""

from pathlib import Path
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_b_collision"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "B", "status": "FAIL", "stage": "initializing"}

try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case B - Particle Wall Collision")
    project_path = OUTPUT_DIR / "case_b_collision.rocky"
    project.SaveProject(str(project_path))

    materials = study.GetMaterialCollection()
    particle_material = materials.GetDefaultParticleMaterial()
    wall_material = materials.GetDefaultBoundaryMaterial()
    particle_material.SetDensity(2500.0, "kg/m3")
    particle_material.SetYoungsModulus(1.0e5, "Pa")
    wall_material.SetDensity(7800.0, "kg/m3")
    wall_material.SetYoungsModulus(1.0e7, "Pa")
    interaction = materials.GetMaterialsInteractionCollection().GetMaterialsInteraction(
        particle_material, wall_material
    )
    target_restitution = 0.70
    interaction.SetRestitutionCoefficient(target_restitution)
    interaction.SetStaticFriction(0.0)
    interaction.SetDynamicFriction(0.0)

    particle = study.CreateParticle()
    particle.SetName("Impact Sphere")
    particle.SetMaterial(particle_material)
    particle.GetSizeDistributionList()[0].SetSize(0.01, "m")

    wall = study.ImportWall(str(ROOT / "assets" / "rocky" / "floor.stl"))[0]
    wall.SetName("Rigid Floor")
    wall.SetMaterial(wall_material)

    release = study.CreateCircularSurface()
    release.SetCenter((0.0, 0.0, 0.03), "m")
    release.SetMaxRadius(0.02, "m")
    release.SetOrientationFromBasisVector(
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    )
    inlet = study.CreateParticleInlet(release, particle)
    inlet.SetInjectionDuration(0.02, "s")
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(1.0, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.001, "kg/s")

    physics = study.GetPhysics()
    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(0.0, "m/s2")

    study.GetContactData().EnableCollectContactsData()
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.05, -0.05, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((0.05, 0.05, 0.06), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(0.06, "s")
    solver.SetTimeInterval(0.0005, "s")
    project.SaveProject(str(project_path))
    result["stage"] = "simulation"
    result["simulation_result"] = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    particle_table = OUTPUT_DIR / "particles.csv"
    particle_metadata = export_particle_table(study, particle_table)
    particles = study.GetParticles()
    time_set = study.GetTimeSet()
    time_steps = list(time_set.GetTimeSteps())
    time_values = [float(value) for value in time_set.GetValues("s")]
    velocity_gf = particles.GetGridFunction("Velocity : Translational : Z")
    particle_id_gf = particles.GetGridFunction("Particle ID")
    velocity_series = []
    for time_value, time_step in zip(time_values, time_steps):
        velocity_gf.SetCurrentTimeStep(time_step)
        particle_id_gf.SetCurrentTimeStep(time_step)
        velocities = velocity_gf.GetArray().tolist()
        ids = particle_id_gf.GetArray().tolist()
        if ids:
            velocity_series.append((time_value, float(velocities[0])))

    contacts = study.GetContactData()
    available_contacts = set(contacts.GetGridFunctionNames())
    force_name = (
        "Normal Force Magnitude"
        if "Normal Force Magnitude" in available_contacts
        else ("Force : Normal" if "Force : Normal" in available_contacts else None)
    )
    overlap_name = "Overlap" if "Overlap" in available_contacts else None
    force_gf = contacts.GetGridFunction(force_name) if force_name else None
    overlap_gf = contacts.GetGridFunction(overlap_name) if overlap_name else None
    contact_samples = []
    for time_value, time_step in zip(time_values, time_steps):
        forces = []
        overlaps = []
        if force_gf is not None:
            force_gf.SetCurrentTimeStep(time_step)
            forces = [abs(float(value)) for value in force_gf.GetArray().tolist()]
        if overlap_gf is not None:
            overlap_gf.SetCurrentTimeStep(time_step)
            overlaps = [float(value) for value in overlap_gf.GetArray().tolist()]
        if forces or overlaps:
            contact_samples.append(
                {
                    "time_s": time_value,
                    "max_normal_force_n": max(forces, default=0.0),
                    "max_overlap_m": max(overlaps, default=0.0),
                }
            )

    negative = [(t, v) for t, v in velocity_series if v < -1.0e-4]
    positive = [(t, v) for t, v in velocity_series if v > 1.0e-4]
    incident = min((v for _, v in negative), default=math.nan)
    rebound = max((v for _, v in positive), default=math.nan)
    measured_restitution = abs(rebound / incident) if incident < 0 and rebound > 0 else math.nan
    contact_duration = (
        contact_samples[-1]["time_s"] - contact_samples[0]["time_s"] + 0.0005
        if contact_samples
        else 0.0
    )
    max_force = max((item["max_normal_force_n"] for item in contact_samples), default=0.0)
    max_overlap = max((item["max_overlap_m"] for item in contact_samples), default=0.0)
    restitution_error = abs(measured_restitution - target_restitution)
    passed = (
        result["simulation_result"]
        and particle_metadata["row_count"] > 0
        and math.isfinite(measured_restitution)
        and restitution_error <= 0.12
        and rebound > 0
        and max_force > 0
        and max_overlap > 0
    )
    result.update(
        {
            "status": "PASS" if passed else "FAIL",
            "stage": "validation",
            "target_restitution": target_restitution,
            "incident_velocity_m_per_s": incident,
            "rebound_velocity_m_per_s": rebound,
            "measured_restitution": measured_restitution,
            "restitution_absolute_error": restitution_error,
            "contact_duration_s": contact_duration,
            "maximum_normal_force_n": max_force,
            "maximum_overlap_m": max_overlap,
            "contact_grid_functions": sorted(available_contacts),
            "contact_samples": contact_samples,
            "project": str(project_path),
            "particle_table": str(particle_table),
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
