"""Shared native Rocky 26.1 SPH setup and result helpers.

The installed Student package has no separate FreeFlow executable or Start
Menu entry.  Its real SPH/FreeFlow solver and PrePost API are hosted by
Rocky.exe/RockySolver.exe, so this suite uses that supported headless path.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "sph_free_surface"
LOG_ROOT = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs")) / "sph_free_surface"
ASSET_ROOT = ROOT / "assets" / "rocky"
ROCKY_EXE = Path(r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\rocky\bin\Rocky.exe")
ROCKY_SOLVER_EXE = ROCKY_EXE.with_name("RockySolver.exe")
PYROCKY_VERSION = "0.4.1"
PRODUCT_VERSION = "26.1.0"
WATER_DENSITY = 998.2
WATER_VISCOSITY = 1.002e-3
GRAVITY = 9.81


def ensure_directories() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def finite(values) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def configure_water_sph(
    study,
    *,
    size_m: float,
    solver_model: str = "IISPH",
    viscosity_pa_s: float = WATER_VISCOSITY,
    thermal: bool = False,
):
    """Enable native SPH and return (settings, water material, physics)."""
    water = study.CreateFluidMaterial("Water")
    water.SetDensity(WATER_DENSITY, "kg/m3")
    water.SetViscosity(viscosity_pa_s, "Pa.s")
    water.SetSpecificHeat(4182.0, "J/kg.K")
    water.SetThermalConductivity(0.598, "W/m.K")
    sph = study.GetSphSettings()
    sph.SetFluidMaterial(water)
    sph.SetSize(size_m, "m")
    sph.SetSolverModel(solver_model)
    sph.SetMaximumExpectedVelocity(3.0, "m/s")
    sph.SetEnabled(True)
    physics = study.GetPhysics()
    physics.SetGravityXDirection(0.0, "m/s2")
    physics.SetGravityYDirection(0.0, "m/s2")
    physics.SetGravityZDirection(-GRAVITY, "m/s2")
    if thermal:
        physics.SetEnableThermalModel(True)
    return sph, water, physics


def add_sph_volume(
    study,
    *,
    name: str,
    center_m: Sequence[float],
    dimensions_m: Sequence[float],
    sph_size_m: float,
    density_kg_m3: float = WATER_DENSITY,
    temperature_k: float = 293.15,
    initial_velocity_m_s: Sequence[float] = (0.0, 0.0, 0.0),
):
    """Create a native SPH Volume Fill while satisfying Rocky's shared DEM schema.

    Rocky 26.1 requires a DEM particle entry whose geometric volume is at least
    one SPH unit volume.  The entry gets a sub-particle total DEM mass, so no DEM
    particle is generated; only the explicitly requested SPH mass is created.
    """
    schema_particle = study.CreateParticle()
    schema_particle.SetName(f"{name} schema particle (not generated)")
    schema_diameter = 1.5 * sph_size_m
    schema_particle.GetSizeDistributionList()[0].SetSize(schema_diameter, "m")
    volume = float(dimensions_m[0]) * float(dimensions_m[1]) * float(dimensions_m[2])
    fill = study.CreateVolumetricInlet(
        particle=schema_particle,
        name=name,
        mass=1.0e-12,
        box_center=tuple(center_m),
        box_dimensions=tuple(dimensions_m),
        use_box_center_as_seed_point=True,
    )
    fill.SetSphMass(density_kg_m3 * volume, "kg")
    fill.SetSphTemperature(temperature_k, "K")
    # The shared DEM/SPH inlet validator also checks the dormant schema
    # particle's temperature whenever the global thermal model is enabled.
    fill.GetInputPropertiesList()[0].SetTemperature(temperature_k, "K")
    fill.SetInitialVelocity(tuple(initial_velocity_m_s), "m/s")
    return fill


def import_open_tank(study, *, name: str = "Open Tank", asset: str = "sph_open_tank.stl"):
    wall = study.ImportWall(str(ASSET_ROOT / asset))[0]
    wall.SetName(name)
    valid = list(wall.GetValidSphBoundaryTypeValues())
    preferred = next((v for v in valid if "no" in v.lower() and "slip" in v.lower()), None)
    if preferred is not None:
        wall.SetSphBoundaryType(preferred)
    return wall, valid


def set_domain(study, minimum=(-0.20, -0.08, -0.05), maximum=(0.20, 0.08, 0.20)) -> None:
    domain = study.GetDomainSettings()
    domain.DisableUseBoundaryLimits()
    domain.SetCoordinateLimitsMinValues(tuple(minimum), "m")
    domain.SetCoordinateLimitsMaxValues(tuple(maximum), "m")


def solve(study, project, project_path: str | Path, *, duration_s: float, output_dt_s: float) -> bool:
    solver = study.GetSolver()
    solver.SetSimulationDuration(duration_s, "s")
    solver.SetTimeInterval(output_dt_s, "s")
    project.SaveProject(str(project_path))
    launched = bool(study.StartSimulation())
    study.RefreshResults()
    project.SaveProject(str(project_path))
    time_set = study.GetTimeSet()
    return bool(launched and time_set is not None and len(list(time_set.GetTimeSteps())) >= 2)
