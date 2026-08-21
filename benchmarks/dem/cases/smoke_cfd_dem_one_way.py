"""Case I: real Fluent F2R field driving Rocky particles (one-way CFD-DEM)."""

from pathlib import Path
import csv
import json
import math
import traceback

from rocky_field_export import export_particle_table, write_eulerian_metadata


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_i_one_way"
FLOW_DIR = OUTPUT_DIR / "low_speed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "I", "status": "FAIL", "stage": "initializing"}

try:
    f2r = FLOW_DIR / "fluent_to_rocky.f2r"
    if not f2r.is_file():
        raise FileNotFoundError(f"Official Fluent F2R export is missing: {f2r}")
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case I - Fluent to Rocky One-Way CFD-DEM")
    project_path = OUTPUT_DIR / "case_i_one_way.rocky"
    project.SaveProject(str(project_path))

    materials = study.GetMaterialCollection()
    pm = materials.GetDefaultParticleMaterial()
    pm.SetDensity(2500.0, "kg/m3")
    # No contacts are expected; a soft tracer avoids an unnecessarily tiny
    # contact-controlled DEM timestep while leaving drag/mass physics intact.
    pm.SetYoungsModulus(1.0e3, "Pa")
    particle = study.CreateParticle()
    particle.SetName("200 micron tracer sphere")
    particle.SetMaterial(pm)
    diameter = 2.0e-4
    particle.GetSizeDistributionList()[0].SetSize(diameter, "m")

    cfd_root = study.GetCFDCoupling()
    coupling = cfd_root.SetupOneWayFluent(str(f2r))
    if coupling is None:
        coupling = cfd_root.GetCouplingProcess()
    params = list(coupling.GetCFDParametersList())
    if not params:
        raise RuntimeError("Rocky did not create per-particle CFD parameters")
    valid_drag_laws = list(params[0].GetValidDragLawValues())
    # The generic list also exposes dense-coupling laws that the one-way
    # process rejects. Schiller-Naumann is accepted here and tends to Stokes
    # drag in this sub-unity particle-Reynolds-number benchmark.
    selected_drag = next((v for v in valid_drag_laws if "schiller" in v.lower()), "SchillerNaumann1933")
    params[0].SetDragLaw(selected_drag)
    coupling.SetUseTurbulentDispersion(False)
    available_boundaries = list(coupling.GetAvailableCoupledBoundaryNames())
    pipe_boundaries = [name for name in available_boundaries if "wall" in name.lower()]
    if pipe_boundaries:
        coupling.CreateCoupledBoundaries(pipe_boundaries)

    surface = study.CreateCircularSurface()
    surface.SetName("Particle release in Fluent pipe")
    surface.SetCenter((0.01, 0.0, 0.0), "m")
    surface.SetMaxRadius(0.001, "m")
    surface.SetOrientationFromBasisVector(
        (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)
    )
    inlet = study.CreateParticleInlet(surface, particle)
    inlet.SetStartTime(0.0, "s")
    inlet.SetStopTime(0.01, "s")
    inlet.SetInjectionDuration(0.01, "s")
    inlet.DisablePeriodic()
    inlet.EnableForcePacking()
    inlet.EnableUseTargetNormalVelocity()
    initial_velocity = 0.001
    inlet.SetTargetNormalVelocity(initial_velocity, "m/s")
    inlet.GetInputPropertiesList()[0].SetMassFlowRate(1.1e-6, "kg/s")

    physics = study.GetPhysics()
    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(0.0, "m/s2")
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues((-0.02, -0.02, -0.02), "m")
    domain.SetCoordinateLimitsMaxValues((1.02, 0.02, 0.02), "m")
    solver = study.GetSolver()
    solver.SetSimulationDuration(0.40, "s")
    solver.SetTimeInterval(0.02, "s")
    project.SaveProject(str(project_path))
    simulation_result = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))

    table_path = OUTPUT_DIR / "particles.csv"
    metadata = export_particle_table(study, table_path)
    rows = [r for r in csv.DictReader(table_path.open(encoding="utf-8")) if r.get("particle_id")]
    by_id = {}
    for row in rows:
        by_id.setdefault(row["particle_id"], []).append(row)
    trajectory = max(by_id.values(), key=len) if by_id else []
    trajectory.sort(key=lambda r: float(r["time_s"]))
    history = [
        {
            "time_s": float(r["time_s"]),
            "x_m": float(r["position_x_m"]),
            "velocity_x_m_per_s": float(r["velocity_x_m_per_s"]),
        }
        for r in trajectory
    ]
    fluid_bulk_velocity = 0.10
    fluid_reference_velocity = 2.0 * fluid_bulk_velocity
    rho_p = 2500.0
    mu = 1.7894e-5
    tau_stokes = rho_p * diameter * diameter / (18.0 * mu)
    theory = []
    if history:
        t0 = history[0]["time_s"]
        v0 = history[0]["velocity_x_m_per_s"]
        for sample in history:
            dt = sample["time_s"] - t0
            # The tracer is released on the pipe centerline. Fully developed
            # laminar circular-pipe theory gives U_center = 2 U_bulk.
            velocity = fluid_reference_velocity - (fluid_reference_velocity - v0) * math.exp(-dt / tau_stokes)
            position = history[0]["x_m"] + fluid_reference_velocity * dt - (fluid_reference_velocity - v0) * tau_stokes * (1.0 - math.exp(-dt / tau_stokes))
            theory.append({**sample, "stokes_velocity_m_per_s": velocity, "stokes_x_m": position})
    velocities = [x["velocity_x_m_per_s"] for x in history]
    monotonic_violations = sum(b + 1.0e-8 < a for a, b in zip(velocities, velocities[1:]))
    final_velocity = velocities[-1] if velocities else math.nan
    stokes_final = theory[-1]["stokes_velocity_m_per_s"] if theory else math.nan
    final_relative_error = abs(final_velocity - stokes_final) / max(abs(stokes_final), 1e-12)
    flow_files = sorted(str(path.resolve()) for path in FLOW_DIR.glob("fluent_to_rocky*"))
    write_eulerian_metadata(OUTPUT_DIR / "eulerian_flow_metadata.json", {
        "solver": "Ansys Fluent 2026 R1 Student",
        "mesh": "3-D 11,520-cell hexahedral circular pipe",
        "flow_regime": "steady laminar",
        "bulk_velocity_m_per_s": fluid_bulk_velocity,
        "density_kg_per_m3": 1.225,
        "viscosity_Pa_s": mu,
        "source_files": flow_files,
        "coupling": "official Fluent Rocky Export .f2r",
    })
    checks = {
        "simulation_completed": simulation_result,
        "official_f2r_imported": f2r.is_file() and len(flow_files) >= 3,
        "particle_trajectory_available": len(history) >= 5,
        "particle_accelerates_with_flow": len(velocities) >= 2 and final_velocity > velocities[0] + 0.01,
        "relaxation_is_monotonic": monotonic_violations <= 1,
        "stokes_relaxation_sanity": math.isfinite(final_relative_error) and final_relative_error < 0.40,
    }
    result.update({
        "status": "PASS" if all(checks.values()) else "FAIL",
        "stage": "validation",
        "simulation_result": simulation_result,
        "coupling_mode": cfd_root.GetCouplingMode(),
        "f2r": str(f2r),
        "available_coupled_boundaries": available_boundaries,
        "created_coupled_boundaries": pipe_boundaries,
        "valid_drag_laws": valid_drag_laws,
        "selected_drag_law": selected_drag,
        "particle_diameter_m": diameter,
        "particle_density_kg_m3": rho_p,
        "fluid_bulk_velocity_m_per_s": fluid_bulk_velocity,
        "fluid_centerline_reference_velocity_m_per_s": fluid_reference_velocity,
        "stokes_relaxation_time_s": tau_stokes,
        "final_particle_velocity_m_per_s": final_velocity,
        "stokes_final_velocity_m_per_s": stokes_final,
        "stokes_final_relative_error": final_relative_error,
        "monotonic_velocity_violations": monotonic_violations,
        "trajectory": theory,
        "checks": checks,
        "particle_rows": metadata["row_count"],
        "particle_table": str(table_path),
        "eulerian_metadata": str(OUTPUT_DIR / "eulerian_flow_metadata.json"),
        "project": str(project_path),
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
