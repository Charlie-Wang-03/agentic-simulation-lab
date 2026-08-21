"""Case E: real Rocky hopper filling followed by timed sliding-gate discharge."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_e_hopper"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "E", "status": "FAIL", "stage": "initializing"}

try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case E - Sliding Gate Hopper Discharge")
    project_path = OUTPUT_DIR / "case_e_hopper.rocky"
    project.SaveProject(str(project_path))

    materials = study.GetMaterialCollection()
    pm = materials.GetDefaultParticleMaterial()
    wm = materials.GetDefaultBoundaryMaterial()
    pm.SetDensity(1500.0, "kg/m3")
    pm.SetYoungsModulus(2.0e6, "Pa")
    wm.SetYoungsModulus(1.0e7, "Pa")
    interactions = materials.GetMaterialsInteractionCollection()
    for m1, m2 in ((pm, pm), (pm, wm)):
        interaction = interactions.GetMaterialsInteraction(m1, m2)
        interaction.SetRestitutionCoefficient(0.25)
        interaction.SetStaticFriction(0.45)
        interaction.SetDynamicFriction(0.36)

    particle = study.CreateParticle()
    particle.SetName("Hopper Grain")
    particle.SetMaterial(pm)
    particle.GetSizeDistributionList()[0].SetSize(0.006, "m")
    particle.SetRollingResistance(0.15)
    physics = study.GetPhysics()
    valid_rolling = list(physics.GetValidRollingResistanceModelValues())
    rolling_model = next((v for v in valid_rolling if v.lower() != "none"), valid_rolling[-1])
    physics.SetRollingResistanceModel(rolling_model)

    hopper = study.ImportWall(str(ROOT / "assets" / "rocky" / "hopper.stl"))[0]
    gate = study.ImportWall(str(ROOT / "assets" / "rocky" / "hopper_gate.stl"))[0]
    hopper.SetName("Hopper Walls")
    gate.SetName("Sliding Gate")
    hopper.SetMaterial(wm)
    gate.SetMaterial(wm)

    frame = study.GetMotionFrameSource().NewFrame()
    frame.SetName("Timed Gate Translation")
    frame.AddTranslationMotion(
        start_time=(0.80, "s"), stop_time=(1.30, "s"),
        velocity=((0.12, 0.0, 0.0), "m/s"),
    )
    frame.ApplyTo(gate)

    outlet_surface = study.CreateRectangularSurface()
    outlet_surface.SetCenter((0.0, 0.0, 0.010), "m")
    outlet_surface.SetLength(0.030, "m")
    outlet_surface.SetWidth(0.030, "m")
    outlet = study.CreateOutlet(outlet_surface)
    outlet.SetName("Hopper Outlet")

    inlet_surface = study.CreateCircularSurface()
    inlet_surface.SetCenter((0.0, 0.0, 0.095), "m")
    inlet_surface.SetMaxRadius(0.025, "m")
    inlet_surface.SetOrientationFromBasisVector(
        (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    )
    inlet = study.CreateParticleInlet(inlet_surface, particle)
    inlet.SetStartTime(0.0, "s")
    inlet.SetStopTime(0.55, "s")
    inlet.SetInjectionDuration(0.55, "s")
    inlet.DisablePeriodic()
    inlet.EnableForcePacking()
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(0.08, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.025, "kg/s")

    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.10, -0.08, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((0.10, 0.08, 0.12), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(2.20, "s")
    solver.SetTimeInterval(0.05, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    table_path = OUTPUT_DIR / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = [r for r in csv.DictReader(table_path.open(encoding="utf-8")) if r.get("particle_id")]
    counts = {}
    mass_by_time = {}
    for row in rows:
        t = float(row["time_s"])
        counts[t] = counts.get(t, 0) + 1
        mass_by_time[t] = mass_by_time.get(t, 0.0) + float(row["particle_mass_kg"])
    history = [
        {"time_s": t, "particle_count": counts[t], "mass_remaining_kg": mass_by_time[t]}
        for t in sorted(counts)
    ]
    peak_index = max(range(len(history)), key=lambda i: history[i]["mass_remaining_kg"])
    peak = history[peak_index]
    final = history[-1]
    discharged_mass = peak["mass_remaining_kg"] - final["mass_remaining_kg"]
    flow_samples = []
    for left, right in zip(history, history[1:]):
        if left["time_s"] >= 0.80:
            dt = right["time_s"] - left["time_s"]
            flow = max(0.0, left["mass_remaining_kg"] - right["mass_remaining_kg"]) / dt
            flow_samples.append({"time_s": right["time_s"], "mass_flow_kg_per_s": flow})
    positive_flows = [x["mass_flow_kg_per_s"] for x in flow_samples if x["mass_flow_kg_per_s"] > 0]
    mean_flow = sum(positive_flows) / len(positive_flows) if positive_flows else 0.0
    cv_flow = (
        math.sqrt(sum((x - mean_flow) ** 2 for x in positive_flows) / len(positive_flows)) / mean_flow
        if positive_flows and mean_flow > 0 else math.inf
    )
    particle_mass = float(rows[0]["particle_mass_kg"]) if rows else math.nan
    count_loss_mass = (peak["particle_count"] - final["particle_count"]) * particle_mass
    conservation_error = abs(discharged_mass - count_loss_mass) / max(peak["mass_remaining_kg"], 1e-15)
    checks = {
        "simulation_completed": simulation_result,
        "filled_before_gate_open": peak["particle_count"] >= 25 and peak["time_s"] <= 1.0,
        "particles_discharged": final["particle_count"] <= 0.75 * peak["particle_count"],
        "positive_discharge_rate": mean_flow > 0.0 and len(positive_flows) >= 2,
        "mass_conservation_from_particle_ids": conservation_error < 1.0e-9,
        "flow_not_single_impulse": len(positive_flows) >= 3,
    }
    result.update({
        "status": "PASS" if all(checks.values()) else "FAIL",
        "stage": "validation",
        "simulation_result": simulation_result,
        "geometry": "3-D square hopper with 24 mm outlet and timed sliding gate",
        "gate_open_time_s": 0.80,
        "particle_diameter_m": 0.006,
        "particle_density_kg_m3": 1500.0,
        "rolling_resistance_model": rolling_model,
        "peak_inventory": peak,
        "final_inventory": final,
        "discharged_mass_kg": discharged_mass,
        "mean_positive_mass_flow_kg_per_s": mean_flow,
        "positive_flow_coefficient_of_variation": cv_flow,
        "mass_conservation_relative_error": conservation_error,
        "history": history,
        "mass_flow_history": flow_samples,
        "checks": checks,
        "project": str(project_path),
        "particle_table": str(table_path),
        "particle_rows": metadata["row_count"],
    })
    project.CloseProject(check_save_state=False)
except Exception:
    result["error"] = traceback.format_exc()
finally:
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        app.Exit()
    except Exception:
        pass
