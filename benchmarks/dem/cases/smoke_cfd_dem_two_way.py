"""Case J: exercise and classify the official Fluent/Rocky two-way setup.

No fallback force model is used. If Rocky's packaged Fluent integration cannot
produce its required mesh metadata, the case is explicitly blocked.
"""

from pathlib import Path
import json
import traceback


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "rocky_dem" / "case_j_two_way"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_PATH = OUTPUT_DIR / "result.json"
result = {"case": "J", "status": "FAIL", "stage": "initializing"}

try:
    project = app.CreateProject()
    study = project.GetStudy()
    study.SetName("Case J - Fluent Rocky Two-Way CFD-DEM")
    project_path = OUTPUT_DIR / "case_j_two_way.rocky"
    project.SaveProject(str(project_path))
    particle = study.CreateParticle()
    particle.SetName("Two-way coupling probe sphere")
    particle.GetSizeDistributionList()[0].SetSize(0.001, "m")
    cas = OUTPUT_DIR / "case_j_unsteady.cas.h5"
    if not cas.is_file():
        raise FileNotFoundError(f"Prepared unsteady Fluent case is missing: {cas}")
    result["stage"] = "SetupTwoWayFluent"
    cfd_root = study.GetCFDCoupling()
    coupling = cfd_root.SetupTwoWayFluent(str(cas))
    if coupling is None:
        coupling = cfd_root.GetCouplingProcess()
    result.update({
        "status": "FAIL",
        "stage": "configured_but_not_simulated",
        "coupling_mode": cfd_root.GetCouplingMode(),
        "error": "Two-way setup unexpectedly configured; a validated physical benchmark is still required.",
    })
except Exception:
    error = traceback.format_exc()
    build_mismatch = "build id 10262" in error and "build id 10261" in error
    missing_mesh_info = "No mesh_info.json file was found" in error
    base_unsteady = False
    try:
        prepare = json.loads((OUTPUT_DIR / "fluent_prepare.json").read_text(encoding="utf-8"))
        base_unsteady = prepare.get("status") == "PASS" and prepare.get("time_mode") == "transient"
    except Exception:
        prepare = {"status": "unavailable"}
    status = "BLOCKED BY CURRENT API" if build_mismatch and missing_mesh_info and base_unsteady else "FAIL"
    result.update({
        "status": status,
        "stage": "official_two_way_setup_validation",
        "blocker": "Rocky 2026 R1's installed Fluent coupling UDF targets build 10261, while Fluent reports build 10262; Rocky consequently receives no required mesh_info.json.",
        "error": error,
        "fluent_base": prepare,
        "attempted_coupling": "study.GetCFDCoupling().SetupTwoWayFluent(case_j_unsteady.cas.h5)",
        "requested_physical_cases": ["packed/low-flow", "approaching fluidization"],
        "physical_results": "NOT RUN - official coupling setup failed before solver launch",
        "synthetic_fallback_used": False,
        "checks": {
            "fluent_base_is_unsteady": base_unsteady,
            "official_two_way_api_called": True,
            "required_mesh_info_created": not missing_mesh_info,
            "packaged_builds_match": not build_mismatch,
            "momentum_exchange_validated": False,
            "fluidization_sanity_validated": False,
        },
    })
finally:
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    try:
        app.Exit()
    except Exception:
        pass
