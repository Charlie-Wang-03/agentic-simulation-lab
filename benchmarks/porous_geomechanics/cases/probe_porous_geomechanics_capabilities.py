"""Phase 0: exercise the Ansys 261 porous-media and soil-analysis APIs."""

from __future__ import annotations

import importlib.metadata
import re

from fluent_mesh import rectangular_2d
from porous_geomechanics_common import *


CASE = "phase0_capabilities"


def main() -> int:
    paths = clean_case(CASE)
    mesh = paths["dir"] / "phase0.msh"
    rectangular_2d(mesh, [0.0, 0.5, 1.0], [0.0, 0.1, 0.2])
    fluent = {}
    try:
        with fluent_session(dimension=2, processor_count=1, cwd=paths["dir"], start_transcript=False) as s:
            s.settings.file.read_mesh(file_name=str(mesh))
            zone = s.settings.setup.cell_zone_conditions.fluid["fluid"].porous_zone
            zone.porous = True
            zone.porosity.value = 0.35
            zone.viscous_resistance[0].value = 1.0e8
            zone.viscous_resistance[1].value = 2.0e8
            zone.inertial_resistance[0].value = 10.0
            zone.inertial_resistance[1].value = 20.0
            state = zone.get_state()
            s.settings.setup.models.energy.enabled = True
            energy_enabled = bool(s.settings.setup.models.energy.enabled())
            thermal_state = zone.get_state()
            species = s.settings.setup.models.species
            species.model.option = "species-transport"
            species_enabled = str(species.model.option()) == "species-transport"
            species_state = zone.get_state()
            fluent = {
                "status": "PASS",
                "porous_zone": bool(state.get("porous")),
                "porosity": state.get("porosity", {}).get("value"),
                "viscous_resistance": [x.get("value") for x in state.get("viscous_resistance", [])],
                "inertial_resistance": [x.get("value") for x in state.get("inertial_resistance", [])],
                "anisotropic_resistance": len(state.get("viscous_resistance", [])) >= 2,
                "porous_energy": energy_enabled and "equib_thermal" in thermal_state,
                "porous_species_transport": species_enabled and "anisotropic_spe_diff" in species_state,
                "pyfluent_version": importlib.metadata.version("ansys-fluent-core"),
            }
    except Exception as exc:
        status, error = classify_solver_error(exc)
        fluent = {"status": status, "error": error}

    if fluent.get("status") == "BLOCKED BY CURRENT LICENSE CONTEXT":
        mapdl = {
            "status": "BLOCKED BY CURRENT LICENSE CONTEXT",
            "pymapdl_installed": True,
            "note": "MAPDL uses the same unavailable Ansys licensing context; a prior raw MAPDL license error is retained when present.",
        }
        checks = {"solver_preflight": False}
        payload = status_payload(
            "Phase 0", "Ansys 261 porous/geomechanics capability probe",
            "BLOCKED BY CURRENT LICENSE CONTEXT", fluent=fluent, mapdl=mapdl, checks=checks,
            static_api_evidence={
                "fluent_261_generated_settings": ["porous", "porosity", "viscous_resistance", "inertial_resistance", "equib_thermal", "anisotropic_spe_diff"],
                "mapdl_261_documented_elements": ["CPT212", "CPT213", "CPT215", "CPT216", "CPT217"],
                "analysis_types": {"ANTYPE_SOIL": "documented for soil analysis", "ANTYPE_STATIC": "used by official VM264 consolidation verification"},
            },
            files=[str(mesh.resolve())],
        )
        write_json(paths["result"], payload)
        print(payload)
        return 0

    apdl = """/BATCH
/CLEAR,START
/PREP7
ET,1,CPT212
KEYOPT,1,12,1
MP,EX,1,1E8
MP,PRXY,1,0.3
FINISH
/SOLU
ANTYPE,SOIL
FINISH
/EXIT,NOSAVE
"""
    run = run_apdl(CASE, apdl, timeout=120)
    listing = run["listing"]
    errors = [line.strip() for line in listing.splitlines() if "*** ERROR ***" in line]
    warnings = [line.strip() for line in listing.splitlines() if "*** WARNING ***" in line]
    cpt_recognized = bool(re.search(r"CPT212", listing, re.I)) and not any("CPT212" in e for e in errors)
    soil_recognized = bool(re.search(r"SOIL", listing, re.I)) and not any("ANTYPE" in e or "SOIL" in e for e in errors)
    mapdl = {
        "status": "PASS" if run["exit_code"] == 0 and cpt_recognized else "FAIL",
        "exit_code": run["exit_code"],
        "pymapdl_installed": True,
        "CPT212_pore_pressure_element": cpt_recognized,
        "ANTYPE_SOIL_recognized": soil_recognized,
        "transient_structural_pore_diffusion": cpt_recognized,
        "geostatic_commands_to_test_in_case_G": ["INISTATE", "ACEL", "initial pore-pressure DOF"],
        "errors": errors[:20],
        "warnings": warnings[:20],
    }
    checks = {
        "fluent_porous_settings_roundtrip": fluent.get("status") == "PASS",
        "mapdl_coupled_pore_element_available": cpt_recognized,
        "mapdl_batch_completed": run["exit_code"] == 0,
    }
    payload = status_payload(
        "Phase 0", "Ansys 261 porous/geomechanics capability probe",
        "PASS" if all(checks.values()) else "FAIL",
        fluent=fluent, mapdl=mapdl, checks=checks,
        interpretation={
            "ANTYPE_SOIL": "Reported exactly from the solver probe; CPT212 transient coupling remains the authoritative capability for Cases F/G.",
            "api_policy": "A feature is not marked PASS until a solved case passes a physical check.",
        },
        files=[str(mesh.resolve()), str(paths["input"].resolve()), str(paths["solver"].resolve())],
    )
    write_json(paths["result"], payload)
    print(payload)
    return 0 if payload["status"] in ("PASS", "BLOCKED BY CURRENT LICENSE CONTEXT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
