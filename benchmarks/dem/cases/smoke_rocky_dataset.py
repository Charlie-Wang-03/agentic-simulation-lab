"""Case K: generate ten real Rocky Lagrangian free-fall parameter cases."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "dataset"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = OUTPUT_DIR / "dataset_index.json"

diameters = [0.008, 0.009, 0.010, 0.011, 0.012]
densities = [1500.0, 2500.0]
case_specs = [
    {"diameter_m": diameter, "density_kg_per_m3": density}
    for density in densities
    for diameter in diameters
]
index = {
    "status": "FAIL",
    "representation": {
        "fluid": "Eulerian mesh fields (not applicable to these DEM-only cases)",
        "particles": "ragged Lagrangian table; no projection to a CFD mesh",
    },
    "cases": [],
}


def run_case(case_number, spec):
    case_id = f"freefall_{case_number:02d}"
    case_dir = OUTPUT_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName(f"Dataset {case_id}")
    project_path = case_dir / f"{case_id}.rocky"
    project.SaveProject(str(project_path))

    material = study.GetMaterialCollection().GetDefaultParticleMaterial()
    material.SetDensity(spec["density_kg_per_m3"], "kg/m3")
    particle = study.CreateParticle()
    particle.SetName(f"Sphere d={spec['diameter_m']:.3f}m")
    particle.SetMaterial(material)
    particle.GetSizeDistributionList()[0].SetSize(spec["diameter_m"], "m")
    inlet_surface = study.CreateCircularSurface()
    inlet_surface.SetCenter((0.0, 0.0, 0.10), "m")
    inlet_surface.SetMaxRadius(0.02, "m")
    inlet = study.CreateParticleInlet(inlet_surface, particle)
    inlet.SetInjectionDuration(0.02, "s")
    inlet.EnableUseTargetNormalVelocity()
    inlet.SetTargetNormalVelocity(0.10, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(0.001, "kg/s")

    physics = study.GetPhysics()
    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-9.81, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.05, -0.05, -0.10), "m")
    domain.SetCoordinateLimitsMaxValues((0.05, 0.05, 0.15), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(0.05, "s")
    solver.SetTimeInterval(0.01, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    table_path = case_dir / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = [
        row
        for row in csv.DictReader(table_path.open(encoding="utf-8"))
        if row.get("particle_id")
    ]
    by_time = {}
    for row in rows:
        by_time.setdefault(float(row["time_s"]), row)
    samples = [by_time[key] for key in sorted(by_time)]
    errors = []
    if samples:
        t0 = float(samples[0]["time_s"])
        z0 = float(samples[0]["position_z_m"])
        v0 = float(samples[0]["velocity_z_m_per_s"])
        for row in samples:
            delta_t = float(row["time_s"]) - t0
            expected_z = z0 + v0 * delta_t - 0.5 * 9.81 * delta_t * delta_t
            errors.append(abs(float(row["position_z_m"]) - expected_z))
    max_error = max(errors, default=math.inf)
    particle_mass_theory = (
        spec["density_kg_per_m3"] * math.pi / 6.0 * spec["diameter_m"] ** 3
    )
    status = (
        "PASS"
        if simulation_result and len(samples) >= 3 and max_error <= 2.0e-3
        else "FAIL"
    )
    case_metadata = {
        "case_id": case_id,
        "status": status,
        "parameters": spec,
        "particle_mass_theory_kg": particle_mass_theory,
        "simulation_duration_s": 0.05,
        "output_interval_s": 0.01,
        "simulation_result": simulation_result,
        "max_freefall_position_error_m": max_error,
        "particle_table": str(table_path),
        "particle_table_metadata": str(table_path.with_suffix(".metadata.json")),
        "project": str(project_path),
        "force_xyz": {
            "available_from_standard_particle_grid_functions": False,
            "note": "No force field was reported by this Rocky particle process; no synthetic force column was inserted.",
        },
        "temperature": {"applicable": False},
        "contact_data": {"applicable": False, "reason": "pre-impact free fall"},
        "export": metadata,
    }
    (case_dir / "case_metadata.json").write_text(
        json.dumps(case_metadata, indent=2), encoding="utf-8"
    )
    project.CloseProject(check_save_state=False)
    return case_metadata


try:
    for case_number, spec in enumerate(case_specs, start=1):
        index["cases"].append(run_case(case_number, spec))
    index["case_count"] = len(index["cases"])
    index["pass_count"] = sum(case["status"] == "PASS" for case in index["cases"])
    index["status"] = (
        "PASS"
        if index["case_count"] == 10 and index["pass_count"] == index["case_count"]
        else "FAIL"
    )
except Exception:
    index["error"] = traceback.format_exc()
finally:
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
    try:
        app.Exit()
    except Exception:
        pass
