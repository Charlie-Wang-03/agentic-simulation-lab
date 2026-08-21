"""Case F: two-species mixing in a real Rocky moving-wall tumbler."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_f_rotating_drum"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "F", "status": "FAIL", "stage": "initializing"}


def centroid_separation(rows):
    groups = {}
    for row in rows:
        # Rocky reports the same geometric Particle Type for these two spheres;
        # Particle Inlet is the stable categorical field that preserves species provenance.
        key = row.get("particle_inlet", "")
        groups.setdefault(key, []).append((float(row["position_x_m"]), float(row["position_z_m"])))
    if len(groups) < 2:
        return math.nan, groups
    keys = sorted(groups)[:2]
    centers = []
    for key in keys:
        pts = groups[key]
        centers.append((sum(x for x, _ in pts) / len(pts), sum(z for _, z in pts) / len(pts)))
    return math.hypot(centers[0][0] - centers[1][0], centers[0][1] - centers[1][1]), groups


try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case F - Two Species Rotating Drum")
    project_path = OUTPUT_DIR / "case_f_rotating_drum.rocky"
    project.SaveProject(str(project_path))
    materials = study.GetMaterialCollection()
    pm = materials.GetDefaultParticleMaterial()
    wm = materials.GetDefaultBoundaryMaterial()
    pm.SetDensity(1800.0, "kg/m3")
    pm.SetYoungsModulus(2.0e6, "Pa")
    wm.SetYoungsModulus(1.0e7, "Pa")
    interactions = materials.GetMaterialsInteractionCollection()
    for m1, m2 in ((pm, pm), (pm, wm)):
        interaction = interactions.GetMaterialsInteraction(m1, m2)
        interaction.SetRestitutionCoefficient(0.35)
        interaction.SetStaticFriction(0.55)
        interaction.SetDynamicFriction(0.44)

    species = []
    for name in ("Species A", "Species B"):
        particle = study.CreateParticle()
        particle.SetName(name)
        particle.SetMaterial(pm)
        particle.GetSizeDistributionList()[0].SetSize(0.005, "m")
        particle.SetRollingResistance(0.10)
        species.append(particle)
    physics = study.GetPhysics()
    valid_rolling = list(physics.GetValidRollingResistanceModelValues())
    rolling_model = next((v for v in valid_rolling if v.lower() != "none"), valid_rolling[-1])
    physics.SetRollingResistanceModel(rolling_model)

    drum = study.ImportWall(str(ROOT / "assets" / "rocky" / "hex_drum.stl"))[0]
    drum.SetName("Rotating Hexagonal Drum")
    drum.SetMaterial(wm)
    rpm = 30.0
    omega = rpm * 2.0 * math.pi / 60.0
    frame = study.GetMotionFrameSource().NewFrame()
    frame.SetName("Drum Rotation 30 RPM")
    frame.SetRelativePosition((0.0, 0.0, 0.06), "m")
    frame.AddRotationMotion(
        start_time=(0.60, "s"), stop_time=(3.00, "s"),
        angular_velocity=((0.0, omega, 0.0), "rad/s"),
    )
    frame.ApplyTo(drum)

    for x, particle, name in ((-0.014, species[0], "A inlet"), (0.014, species[1], "B inlet")):
        surface = study.CreateCircularSurface()
        surface.SetName(name)
        surface.SetCenter((x, 0.0, 0.085), "m")
        surface.SetMaxRadius(0.008, "m")
        surface.SetOrientationFromBasisVector(
            (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
        )
        inlet = study.CreateParticleInlet(surface, particle)
        inlet.SetStartTime(0.0, "s")
        inlet.SetStopTime(0.35, "s")
        inlet.SetInjectionDuration(0.35, "s")
        inlet.DisablePeriodic()
        inlet.EnableForcePacking()
        inlet.EnableUseTargetNormalVelocity()
        inlet.SetTargetNormalVelocity(0.05, "m/s")
        inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.006, "kg/s")

    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.06, -0.04, 0.0), "m")
    domain.SetCoordinateLimitsMaxValues((0.06, 0.04, 0.12), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(3.00, "s")
    solver.SetTimeInterval(0.10, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    table_path = OUTPUT_DIR / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = [r for r in csv.DictReader(table_path.open(encoding="utf-8")) if r.get("particle_id")]
    by_time = {}
    for row in rows:
        by_time.setdefault(float(row["time_s"]), []).append(row)
    history = []
    reference_sep = math.nan
    for time_value in sorted(by_time):
        sample = by_time[time_value]
        sep, groups = centroid_separation(sample)
        if time_value <= 0.60 and math.isfinite(sep):
            reference_sep = sep
        speeds = [math.hypot(float(r["velocity_x_m_per_s"]), float(r["velocity_z_m_per_s"])) for r in sample]
        angular = [abs(float(r["angular_velocity_y_rad_per_s"])) for r in sample]
        mixing = max(0.0, min(1.0, 1.0 - sep / reference_sep)) if math.isfinite(reference_sep) and reference_sep > 0 else math.nan
        history.append({
            "time_s": time_value,
            "particle_count": len(sample),
            "species_counts": {str(k): len(v) for k, v in groups.items()},
            "species_centroid_separation_m": sep,
            "mixing_index": mixing,
            "mean_xz_speed_m_per_s": sum(speeds) / len(speeds),
            "mean_abs_angular_velocity_y_rad_per_s": sum(angular) / len(angular),
        })
    pre = [h for h in history if 0.40 <= h["time_s"] <= 0.60]
    active = [h for h in history if h["time_s"] >= 0.80]
    pre_speed = sum(h["mean_xz_speed_m_per_s"] for h in pre) / len(pre) if pre else math.nan
    active_peak_speed = max((h["mean_xz_speed_m_per_s"] for h in active), default=math.nan)
    max_mixing = max((h["mixing_index"] for h in active if math.isfinite(h["mixing_index"])), default=math.nan)
    mixing_range = (
        max(h["mixing_index"] for h in active if math.isfinite(h["mixing_index"]))
        - min(h["mixing_index"] for h in active if math.isfinite(h["mixing_index"]))
        if any(math.isfinite(h["mixing_index"]) for h in active) else math.nan
    )
    species_keys = sorted({r.get("particle_inlet", "") for r in rows})
    checks = {
        "simulation_completed": simulation_result,
        "two_species_present": len(species_keys) >= 2,
        "adequate_inventory": max((h["particle_count"] for h in history), default=0) >= 20,
        "wall_drives_particle_motion": math.isfinite(active_peak_speed) and active_peak_speed > max(0.03, 1.2 * pre_speed),
        "mixing_metric_changes": math.isfinite(mixing_range) and mixing_range > 0.08,
        "species_centroids_approach": math.isfinite(max_mixing) and max_mixing > 0.10,
    }
    result.update({
        "status": "PASS" if all(checks.values()) else "FAIL",
        "stage": "validation",
        "simulation_result": simulation_result,
        "geometry": "closed horizontal hexagonal drum, axis along y",
        "rpm": rpm,
        "angular_velocity_rad_per_s": omega,
        "motion_start_s": 0.60,
        "particle_diameter_m": 0.005,
        "rolling_resistance_model": rolling_model,
        "species_inlet_ids": species_keys,
        "pre_rotation_mean_xz_speed_m_per_s": pre_speed,
        "active_peak_mean_xz_speed_m_per_s": active_peak_speed,
        "maximum_mixing_index": max_mixing,
        "mixing_index_range": mixing_range,
        "mixing_definition": "1 - instantaneous species-centroid separation / pre-rotation separation; clipped to [0,1]",
        "history": history,
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
