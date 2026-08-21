"""Case H: hot Rocky particle cooling against a cold isothermal wall."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_h_thermal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "H", "status": "FAIL", "stage": "initializing"}

try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case H - Hot Particle Cold Wall")
    project_path = OUTPUT_DIR / "case_h_thermal.rocky"
    project.SaveProject(str(project_path))
    materials = study.GetMaterialCollection()
    particle_material = materials.GetDefaultParticleMaterial()
    wall_material = materials.GetDefaultBoundaryMaterial()
    particle_material.SetDensity(2500.0, "kg/m3")
    particle_material.SetYoungsModulus(1.0e6, "Pa")
    particle_material.SetSpecificHeat(500.0, "J/kg.K")
    particle_material.SetThermalConductivity(100.0, "W/m.K")
    wall_material.SetYoungsModulus(1.0e7, "Pa")
    wall_material.SetSpecificHeat(500.0, "J/kg.K")
    wall_material.SetThermalConductivity(100.0, "W/m.K")
    interaction = materials.GetMaterialsInteractionCollection().GetMaterialsInteraction(
        particle_material, wall_material
    )
    interaction.SetRestitutionCoefficient(0.05)
    interaction.SetStaticFriction(0.5)
    interaction.SetDynamicFriction(0.4)

    particle = study.CreateParticle()
    particle.SetMaterial(particle_material)
    particle.GetSizeDistributionList()[0].SetSize(0.01, "m")
    wall = study.ImportWall(str(ROOT / "assets" / "rocky" / "floor.stl"))[0]
    wall.SetMaterial(wall_material)
    thermal_bc_values = list(wall.GetValidThermalBoundaryConditionTypeValues())
    fixed_bc = next(
        (value for value in thermal_bc_values if "temperature" in value.lower()),
        thermal_bc_values[-1],
    )
    wall.SetThermalBoundaryConditionType(fixed_bc)
    wall.SetTemperature(300.0, "K")

    inlet_surface = study.CreateCircularSurface()
    inlet_surface.SetCenter((0.0, 0.0, 0.02), "m")
    inlet_surface.SetMaxRadius(0.02, "m")
    inlet_surface.SetOrientationFromBasisVector(
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    )
    inlet = study.CreateParticleInlet(inlet_surface, particle)
    inlet.SetInjectionDuration(0.02, "s")
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(0.1, "m/s")
    inlet_props = inlet.GetInputPropertiesList()[0]
    inlet_props.SetMassFlowRate(0.001, "kg/s")
    inlet_props.SetTemperature(500.0, "K")

    physics = study.GetPhysics()
    physics.SetEnableThermalModel(True)
    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.05, -0.05, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((0.05, 0.05, 0.05), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(1.0, "s")
    solver.SetTimeInterval(0.05, "s")
    project.SaveProject(str(project_path))
    result["simulation_result"] = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    table_path = OUTPUT_DIR / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = [
        row
        for row in csv.DictReader(table_path.open(encoding="utf-8"))
        if row.get("particle_id") and row.get("temperature_k")
    ]
    temperatures = [float(row["temperature_k"]) for row in rows]
    masses = [float(row["particle_mass_kg"]) for row in rows]
    initial_temperature = temperatures[0] if temperatures else math.nan
    final_temperature = temperatures[-1] if temperatures else math.nan
    monotonic_violations = sum(
        later > earlier + 1.0e-6
        for earlier, later in zip(temperatures, temperatures[1:])
    )
    mass = masses[-1] if masses else math.nan
    particle_energy_change = mass * 500.0 * (final_temperature - initial_temperature)
    passed = (
        result["simulation_result"]
        and metadata["row_count"] > 0
        and len(temperatures) >= 5
        and final_temperature < initial_temperature
        and final_temperature >= 299.0
        and monotonic_violations == 0
        and particle_energy_change < 0
    )
    result.update(
        {
            "status": "PASS" if passed else "FAIL",
            "stage": "validation",
            "thermal_model_enabled": bool(physics.GetEnableThermalModel()),
            "wall_thermal_bc": fixed_bc,
            "valid_wall_thermal_bcs": thermal_bc_values,
            "initial_particle_temperature_k": initial_temperature,
            "final_particle_temperature_k": final_temperature,
            "temperature_drop_k": initial_temperature - final_temperature,
            "monotonic_cooling_violations": monotonic_violations,
            "particle_energy_change_j": particle_energy_change,
            "energy_balance_scope": "particle energy loss against an isothermal 300 K wall reservoir",
            "project": str(project_path),
            "particle_table": str(table_path),
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
