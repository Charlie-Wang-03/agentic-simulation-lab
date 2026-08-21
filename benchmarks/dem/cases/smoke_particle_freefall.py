"""Case A: one real Rocky particle in gravity before any wall collision."""

from pathlib import Path
import csv
import json
import math
import sys
import traceback


COMMON_DIR = Path(__file__).resolve().parents[1] / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from rocky_field_export import export_particle_table  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_a_freefall"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "A", "status": "FAIL", "stage": "initializing"}

try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case A - Single Particle Free Fall")

    particle = study.CreateParticle()
    particle.SetName("Free Fall Sphere")
    particle.GetSizeDistributionList()[0].SetSize(0.01, "m")

    inlet_surface = study.CreateCircularSurface()
    inlet_surface.SetName("Single Particle Release Surface")
    inlet_surface.SetCenter((0.0, 0.0, 0.10), "m")
    inlet_surface.SetMaxRadius(0.02, "m")
    particle_inlet = study.CreateParticleInlet(inlet_surface, particle)
    particle_inlet.SetInjectionDuration(0.02, "s")
    particle_inlet.EnableUseTargetNormalVelocity()
    particle_inlet.SetTargetNormalVelocity(0.1, "m/s")
    particle_inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.001, "kg/s")

    physics = study.GetPhysics()
    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")

    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.05, -0.05, -0.10), "m")
    domain.SetCoordinateLimitsMaxValues((0.05, 0.05, 0.15), "m")

    solver = study.GetSolver()
    solver.SetSimulationDuration(0.08, "s")
    solver.SetTimeInterval(0.01, "s")
    project_path = OUTPUT_DIR / "case_a_freefall.rocky"
    project.SaveProject(str(project_path))
    result["stage"] = "simulation"
    result["simulation_result"] = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))
    try:
        count_times, count_values = study.GetParticles().GetNumpyCurve("Particles Count")
        result["particle_count_curve"] = {
            "time_s": [float(value) for value in count_times],
            "count": [float(value) for value in count_values],
        }
    except Exception:
        result["particle_count_curve"] = {"unavailable": traceback.format_exc()}

    table_path = OUTPUT_DIR / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = list(csv.DictReader(table_path.open(encoding="utf-8")))
    rows = [row for row in rows if row.get("particle_id")]
    by_time = {}
    for row in rows:
        by_time.setdefault(float(row["time_s"]), row)
    samples = [by_time[key] for key in sorted(by_time)]
    checks = []
    if samples:
        t0 = float(samples[0]["time_s"])
        z0 = float(samples[0]["position_z_m"])
        v0 = float(samples[0]["velocity_z_m_per_s"])
        for row in samples:
            t = float(row["time_s"]) - t0
            z = float(row["position_z_m"])
            velocity = float(row["velocity_z_m_per_s"])
            expected_z = z0 + v0 * t - 0.5 * 9.81 * t * t
            expected_v = v0 - 9.81 * t
            checks.append(
                {
                    "time_s": t,
                    "z_m": z,
                    "expected_z_m": expected_z,
                    "z_error_m": z - expected_z,
                    "velocity_z_m_per_s": velocity,
                    "expected_velocity_z_m_per_s": expected_v,
                    "velocity_error_m_per_s": velocity - expected_v,
                }
            )
    max_z_error = max((abs(item["z_error_m"]) for item in checks), default=math.inf)
    max_v_error = max(
        (abs(item["velocity_error_m_per_s"]) for item in checks), default=math.inf
    )
    passed = (
        result["simulation_result"]
        and metadata["row_count"] > 0
        and len(checks) >= 3
        and max_z_error <= 2.0e-3
        and max_v_error <= 5.0e-2
    )
    result.update(
        {
            "status": "PASS" if passed else "FAIL",
            "stage": "validation",
            "particle_rows": metadata["row_count"],
            "time_samples_with_particle": len(checks),
            "max_position_error_m": max_z_error,
            "max_velocity_error_m_per_s": max_v_error,
            "tolerances": {"position_m": 2.0e-3, "velocity_m_per_s": 5.0e-2},
            "checks": checks,
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
