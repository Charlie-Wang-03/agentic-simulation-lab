"""Minimal elastic 3D cantilever modal analysis driven through PyMechanical."""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ansys.mechanical.core import launch_mechanical


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", PROJECT_DIR / "outputs"))
MESH_STATS_CSV = OUTPUT_DIR / "modal_cantilever_mesh_stats.csv"
RESULT_JSON = OUTPUT_DIR / "modal_cantilever_results.json"
PREPROCESS_INPUT = OUTPUT_DIR / "modal_cantilever_preprocess.inp"
PREPROCESS_OUTPUT = OUTPUT_DIR / "modal_cantilever_preprocess.out"
CDB_FILE = OUTPUT_DIR / "modal_cantilever_model.cdb"

AWP_ROOT261 = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"
EXEC_FILE = AWP_ROOT261 + r"\aisol\bin\winx64\AnsysWBU.exe"
MAPDL_EXEC_FILE = AWP_ROOT261 + r"\ansys\bin\winx64\ANSYS261.exe"

# SI units: uniform elastic rectangular beam along +X.
LENGTH_M = 0.200
WIDTH_M = 0.020
HEIGHT_M = 0.020
YOUNGS_MODULUS_PA = 200.0e9
POISSON_RATIO = 0.30
DENSITY_KG_M3 = 7850.0
ELEMENT_SIZE_M = 0.010
MODE_COUNT = 6
BETA_1 = 1.875104068711961
MAX_ACCEPTABLE_RELATIVE_ERROR = 0.15


def apdl_path(path: Path) -> str:
    return path.resolve().with_suffix("").as_posix()


def build_preprocess_apdl() -> str:
    """Create the elastic solid mesh and fixed-end nodal component as a CDB."""
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID186
MP,EX,1,{YOUNGS_MODULUS_PA:.16g}
MP,PRXY,1,{POISSON_RATIO:.16g}
MP,DENS,1,{DENSITY_KG_M3:.16g}
BLOCK,0,{LENGTH_M:.16g},{-WIDTH_M / 2:.16g},{WIDTH_M / 2:.16g},{-HEIGHT_M / 2:.16g},{HEIGHT_M / 2:.16g}
ESIZE,{ELEMENT_SIZE_M:.16g}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
ALLSEL,ALL
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
NSEL,S,LOC,X,0
CM,FIXED_END,NODE
ALLSEL,ALL
*CFOPEN,'{apdl_path(MESH_STATS_CSV)}','csv'
*VWRITE,NNODES,NELEMS
(F12.0,',',F12.0)
*CFCLOS
CDWRITE,DB,'{apdl_path(CDB_FILE)}','cdb'
FINISH
/EXIT,NOSAVE
"""


def theoretical_first_frequency_hz() -> float:
    area = WIDTH_M * HEIGHT_M
    second_moment = WIDTH_M * HEIGHT_M**3 / 12.0
    omega_1 = (
        BETA_1**2
        * math.sqrt(YOUNGS_MODULUS_PA * second_moment / (DENSITY_KG_M3 * area))
        / LENGTH_M**2
    )
    return omega_1 / (2.0 * math.pi)


def run_mapdl_preprocessor() -> None:
    PREPROCESS_INPUT.write_text(build_preprocess_apdl(), encoding="ascii")
    env = os.environ.copy()
    env.update(
        {
            "AWP_ROOT261": AWP_ROOT261,
            "ANSYS261_DIR": AWP_ROOT261 + r"\ansys",
        }
    )
    command = [
        MAPDL_EXEC_FILE,
        "-b",
        "-np",
        "2",
        "-j",
        "modal_cantilever_preprocess",
        "-dir",
        str(OUTPUT_DIR),
        "-i",
        str(PREPROCESS_INPUT),
        "-o",
        str(PREPROCESS_OUTPUT),
    ]
    print("MAPDL preprocessing command:", subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, cwd=OUTPUT_DIR, env=env, check=False, timeout=180)
    print(f"MAPDL preprocessing exit code: {completed.returncode}", flush=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"MAPDL preprocessing failed with exit code {completed.returncode}; "
            f"see {PREPROCESS_OUTPUT}"
        )
    if not CDB_FILE.is_file():
        raise RuntimeError(f"MAPDL did not create CDB file: {CDB_FILE}")


def read_mesh_stats() -> dict[str, int]:
    with MESH_STATS_CSV.open("r", encoding="utf-8-sig", newline="") as stream:
        row = next(csv.reader(stream))
    if len(row) != 2:
        raise RuntimeError(f"Expected 2 mesh-stat fields, got {row!r}")
    return {
        "node_count": int(float(row[0])),
        "element_count": int(float(row[1])),
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for generated_file in (
        MESH_STATS_CSV,
        RESULT_JSON,
        PREPROCESS_INPUT,
        PREPROCESS_OUTPUT,
        CDB_FILE,
    ):
        generated_file.unlink(missing_ok=True)

    print("=== PyMechanical 3D cantilever modal smoke test ===", flush=True)
    print(f"Python: {sys.executable}", flush=True)
    print(f"Mechanical executable: {EXEC_FILE}", flush=True)
    print(
        "Model: "
        f"L={LENGTH_M} m, b={WIDTH_M} m, h={HEIGHT_M} m, "
        f"E={YOUNGS_MODULUS_PA} Pa, nu={POISSON_RATIO}, "
        f"rho={DENSITY_KG_M3} kg/m^3",
        flush=True,
    )

    run_mapdl_preprocessor()
    mesh_stats = read_mesh_stats()
    print(
        f"Preprocessed mesh: {mesh_stats['node_count']} nodes, "
        f"{mesh_stats['element_count']} elements",
        flush=True,
    )

    mechanical = None
    normally_closed = False
    try:
        mechanical = launch_mechanical(
            exec_file=EXEC_FILE,
            batch=True,
            start_instance=True,
            cleanup_on_exit=True,
            loglevel="INFO",
            additional_envs={"AWP_ROOT261": AWP_ROOT261},
            verbose_mechanical=True,
        )
        print(f"Connected: version={mechanical.version}, alive={mechanical.is_alive}", flush=True)
        if str(mechanical.version) != "261":
            raise RuntimeError(f"Expected Mechanical 261, got {mechanical.version!r}")

        setup_script = f'''\
import json
ExtAPI.DataModel.Project.New()
model_import = Model.GeometryImportGroup.AddModelImport()
model_import.Name = "3D modal cantilever CDB import"
model_import.ModelImportSourceFilePath = {str(CDB_FILE)!r}
model_import.ProcessNodalComponents = True
model_import.ProcessElementComponents = True
model_import.ProcessModelData = True
model_import.ImportMaterials = True
model_import.CreateGeometry = True
import_ok = model_import.Import()
fixed_candidates = ExtAPI.DataModel.GetObjectsByName("FIXED_END")
if len(fixed_candidates) != 1:
    raise RuntimeError("Expected imported FIXED_END named selection")
analysis = Model.AddModalAnalysis()
analysis.Name = "PyMechanical 3D Cantilever Modal"
analysis.AnalysisSettings.MaximumModesToFind = {MODE_COUNT}
fixed_support = analysis.AddFixedSupport()
fixed_support.Name = "Fully fixed x=0 end"
fixed_support.Location = fixed_candidates[0]
mode_results = []
for mode_index in range(1, {MODE_COUNT + 1}):
    mode_result = analysis.Solution.AddTotalDeformation()
    mode_result.Name = "Mode {{}} Total Deformation".format(mode_index)
    mode_result.Mode = mode_index
    mode_results.append(mode_result)
analysis.Solve(True)
analysis.Solution.EvaluateAllResults()
frequencies_hz = [
    float(item.ReportedFrequency.ConvertUnit("Hz").Value) for item in mode_results
]
payload = {{
    "import_ok": bool(import_ok),
    "solution_status": str(analysis.Solution.Status),
    "frequencies_hz": frequencies_hz,
    "mode_numbers": [int(item.Mode) for item in mode_results],
    "fixed_named_selection": fixed_candidates[0].Name,
}}
json.dumps(payload)
'''
        solver = json.loads(
            mechanical.run_python_script(
                setup_script,
                enable_logging=True,
                log_level="INFO",
            )
        )
        frequencies_hz = [float(value) for value in solver["frequencies_hz"]]
        positive_frequencies = [value for value in frequencies_hz if value > 0.0]
        theoretical_hz = theoretical_first_frequency_hz()
        ansys_first_hz = positive_frequencies[0] if positive_frequencies else float("nan")
        relative_error = abs(ansys_first_hz - theoretical_hz) / theoretical_hz

        checks = {
            "mechanical_version_is_261": str(mechanical.version) == "261",
            "model_import_succeeded": bool(solver["import_ok"]),
            "solution_status_done": solver["solution_status"] == "Done",
            "mesh_has_nodes_and_elements": (
                mesh_stats["node_count"] > 0 and mesh_stats["element_count"] > 0
            ),
            "at_least_six_frequencies": len(positive_frequencies) >= MODE_COUNT,
            "first_frequency_positive_and_finite": (
                ansys_first_hz > 0.0 and math.isfinite(ansys_first_hz)
            ),
            "frequencies_are_nondecreasing": all(
                positive_frequencies[index] <= positive_frequencies[index + 1]
                for index in range(len(positive_frequencies) - 1)
            ),
            "first_frequency_relative_error_within_limit": (
                relative_error <= MAX_ACCEPTABLE_RELATIVE_ERROR
            ),
        }

        result = {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mechanical": {
                "version": str(mechanical.version),
                "product_version": mechanical.run_python_script(
                    "ExtAPI.DataModel.Project.ProductVersion"
                ),
                "grpc_connected": bool(mechanical.is_alive),
                "solution_status": solver["solution_status"],
            },
            "model": {
                "element_type": "SOLID186",
                "length_m": LENGTH_M,
                "width_m": WIDTH_M,
                "height_m": HEIGHT_M,
                "youngs_modulus_pa": YOUNGS_MODULUS_PA,
                "poisson_ratio": POISSON_RATIO,
                "density_kg_m3": DENSITY_KG_M3,
                "nominal_element_size_m": ELEMENT_SIZE_M,
                "boundary_condition": "fully fixed x=0 end",
            },
            "mesh": mesh_stats,
            "results": {
                "requested_mode_count": MODE_COUNT,
                "mode_numbers": solver["mode_numbers"],
                "frequencies_hz": positive_frequencies[:MODE_COUNT],
                "ansys_first_frequency_hz": ansys_first_hz,
                "theoretical_first_frequency_hz": theoretical_hz,
                "relative_error": relative_error,
                "relative_error_percent": relative_error * 100.0,
            },
            "acceptance": {
                "maximum_allowed_relative_error": MAX_ACCEPTABLE_RELATIVE_ERROR,
                "checks": checks,
            },
            "files": {
                "imported_cdb": str(CDB_FILE),
                "mesh_stats_csv": str(MESH_STATS_CSV),
                "mapdl_preprocess_input": str(PREPROCESS_INPUT),
                "mapdl_preprocess_output": str(PREPROCESS_OUTPUT),
            },
        }
        RESULT_JSON.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print(f"Mechanical solution status: {solver['solution_status']}", flush=True)
        print(
            f"Mesh: {mesh_stats['node_count']} nodes, "
            f"{mesh_stats['element_count']} elements",
            flush=True,
        )
        print(
            "First 6 frequencies [Hz]: "
            + ", ".join(f"{value:.6f}" for value in positive_frequencies[:MODE_COUNT]),
            flush=True,
        )
        print(f"Ansys first frequency: {ansys_first_hz:.9f} Hz", flush=True)
        print(f"Euler-Bernoulli first frequency: {theoretical_hz:.9f} Hz", flush=True)
        print(f"Relative error: {relative_error:.3%}", flush=True)
        print(f"JSON results: {RESULT_JSON}", flush=True)

        if result["status"] != "PASS":
            failed = [name for name, passed in checks.items() if not passed]
            raise RuntimeError(f"Acceptance checks failed: {failed}")

        print("=== MODAL SMOKE TEST PASS ===", flush=True)
        return 0
    finally:
        if mechanical is not None:
            print("=== Closing Mechanical normally ===", flush=True)
            mechanical.exit(force=False)
            normally_closed = not mechanical.is_alive
            print(f"Alive after exit: {mechanical.is_alive}", flush=True)
        if RESULT_JSON.is_file():
            result = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
            result["mechanical"]["normally_closed"] = normally_closed
            if not normally_closed:
                result["status"] = "FAIL"
            RESULT_JSON.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    raise SystemExit(main())
