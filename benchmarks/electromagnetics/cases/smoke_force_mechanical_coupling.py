"""Case H: solve Maxwell force, transfer its numeric value, solve Mechanical deformation."""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import traceback
from pathlib import Path

from aedt_smoke_common import OUTPUT_ROOT, aedt_pid_set, aedt_processes, cleanup_new_aedt_processes, ensure_dirs, prepare_pyaedt_student_runtime, student_launch_kwargs, utc_now, write_json


AWP_ROOT261 = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"
MECH_EXE = AWP_ROOT261 + r"\aisol\bin\winx64\AnsysWBU.exe"
MAPDL_EXE = AWP_ROOT261 + r"\ansys\bin\winx64\ANSYS261.exe"


def _apdl_path(path: Path) -> str:
    return path.resolve().with_suffix("").as_posix()


def main() -> int:
    ensure_dirs()
    case_dir = OUTPUT_ROOT / "case_h_force_mechanical"
    case_dir.mkdir(parents=True, exist_ok=True)
    result = {"case": "H", "name": "Maxwell force to Mechanical structural", "timestamp_utc": utc_now(), "status": "FAIL"}
    baseline = aedt_pid_set()
    maxwell = mechanical = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Maxwell2d
        from ansys.aedt.core.generic.constants import SolutionsMaxwell2D

        maxwell = Maxwell2d(project="CaseH_ForceTransfer", design="ForceSource", solution_type=SolutionsMaxwell2D.MagnetostaticXY, **student_launch_kwargs(runtime))
        maxwell.modeler.model_units = "mm"
        inner = maxwell.modeler.create_circle([2, 0, 0], 5, name="LoadedConductor", material="copper")
        shield = maxwell.modeler.create_circle([0, 0, 0], 20, name="ReturnConductor", material="copper")
        hole = maxwell.modeler.create_circle([0, 0, 0], 19, name="ReturnHole", material="vacuum")
        maxwell.modeler.subtract(shield, hole, keep_originals=False)
        region = maxwell.modeler.create_region(50, name="AirRegion")
        maxwell.model_depth = "100mm"
        maxwell.assign_current(inner.name, amplitude="1000A", name="DriveCurrent")
        maxwell.assign_current(shield.name, amplitude="1000A", swap_direction=True, name="ReturnCurrent")
        maxwell.assign_vector_potential(region.edges, vector_value=0, boundary="VectorPotential0")
        force_parameter = maxwell.assign_force([inner.name], force_name="TransferForce")
        maxwell.mesh.assign_length_mesh([inner.name, shield.name], inside_selection=True, maximum_length="3mm", name="ForceMesh")
        setup = maxwell.create_setup("EMSetup", MaximumPasses=1, PercentError=5.0)
        em_solved = bool(maxwell.analyze(setup=setup.name, cores=2, use_auto_settings=False))
        em_messages = list(maxwell.odesktop.GetMessages(maxwell.project_name, maxwell.design_name, 0))
        solution = "EMSetup : LastAdaptive"
        quantities = list(maxwell.post.available_report_quantities(solution=solution))
        force_expressions = [q for q in quantities if q.startswith("TransferForce.Force_")]
        force_values = {}
        if em_solved and force_expressions:
            data = maxwell.post.get_solution_data(expressions=force_expressions, setup_sweep_name=solution)
            if data:
                for expression in force_expressions:
                    _, values = data.get_expression_data(expression=expression, formula="real", convert_to_SI=True)
                    if len(values):
                        force_values[expression] = float(values[0])
        source_force_n = force_values.get("TransferForce.Force_x")
        if source_force_n is None:
            source_force_n = force_values.get("TransferForce.Force_mag")
        if source_force_n is None or not math.isfinite(source_force_n) or abs(source_force_n) <= 0:
            raise RuntimeError(f"No finite nonzero Maxwell force found; quantities={quantities}, values={force_values}")
        source_force_n = abs(source_force_n)
        em_project = case_dir / "case_h_maxwell_source.aedt"
        maxwell.save_project(em_project)
        maxwell.release_desktop(close_projects=True, close_desktop=True)
        maxwell = None

        length, width, height, youngs, poisson, element_size = 0.2, 0.02, 0.02, 200e9, 0.30, 0.01
        cdb = case_dir / "mechanical_force_target.cdb"
        mesh_csv = case_dir / "mechanical_mesh.csv"
        apdl_input = case_dir / "mechanical_preprocess.inp"
        apdl_output = case_dir / "mechanical_preprocess.out"
        apdl = f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID186
MP,EX,1,{youngs:.16g}
MP,PRXY,1,{poisson:.16g}
BLOCK,0,{length:.16g},{-width/2:.16g},{width/2:.16g},{-height/2:.16g},{height/2:.16g}
ESIZE,{element_size:.16g}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
NSEL,S,LOC,X,0
CM,FIXED_END,NODE
NSEL,S,LOC,X,{length:.16g}
CM,LOADED_END,NODE
ALLSEL,ALL
*CFOPEN,'{_apdl_path(mesh_csv)}','csv'
*VWRITE,NNODES,NELEMS
(F12.0,',',F12.0)
*CFCLOS
CDWRITE,DB,'{_apdl_path(cdb)}','cdb'
FINISH
/EXIT,NOSAVE
"""
        apdl_input.write_text(apdl, encoding="ascii")
        env = os.environ.copy()
        env.update({"AWP_ROOT261": AWP_ROOT261, "ANSYS261_DIR": AWP_ROOT261 + r"\ansys"})
        command = [MAPDL_EXE, "-b", "-np", "2", "-j", "case_h_mesh", "-dir", str(case_dir), "-i", str(apdl_input), "-o", str(apdl_output)]
        pre = subprocess.run(command, cwd=case_dir, env=env, timeout=180, check=False)
        if pre.returncode != 0 or not cdb.exists():
            raise RuntimeError(f"MAPDL preprocessing failed with exit code {pre.returncode}")
        with mesh_csv.open(encoding="utf-8-sig") as stream:
            mesh_row = next(csv.reader(stream))
        mesh = {"node_count": int(float(mesh_row[0])), "element_count": int(float(mesh_row[1]))}

        from ansys.mechanical.core import launch_mechanical
        mechanical = launch_mechanical(exec_file=MECH_EXE, batch=True, start_instance=True, cleanup_on_exit=True, loglevel="INFO", additional_envs={"AWP_ROOT261": AWP_ROOT261})
        mechanical_script = f'''
import json
ExtAPI.DataModel.Project.New()
imp = Model.GeometryImportGroup.AddModelImport()
imp.ModelImportSourceFilePath = {str(cdb)!r}
imp.ProcessNodalComponents = True
imp.ProcessElementComponents = True
imp.ProcessModelData = True
imp.ImportMaterials = True
imp.CreateGeometry = True
import_ok = imp.Import()
fixed = ExtAPI.DataModel.GetObjectsByName("FIXED_END")[0]
loaded = ExtAPI.DataModel.GetObjectsByName("LOADED_END")[0]
analysis = Model.AddStaticStructuralAnalysis()
analysis.Name = "Maxwell Force Transfer"
support = analysis.AddFixedSupport()
support.Location = fixed
load = analysis.AddForce()
load.Name = "Imported Maxwell Force"
load.Location = loaded
load.DefineBy = LoadDefineBy.Components
load.XComponent.Output.DiscreteValues = [Quantity("{source_force_n:.16g} [N]")]
load.YComponent.Output.DiscreteValues = [Quantity("0 [N]")]
load.ZComponent.Output.DiscreteValues = [Quantity("0 [N]")]
deformation = analysis.Solution.AddTotalDeformation()
stress = analysis.Solution.AddEquivalentStress()
analysis.Solve(True)
analysis.Solution.EvaluateAllResults()
json.dumps({{"import_ok": bool(import_ok), "status": str(analysis.Solution.Status), "deformation_m": deformation.Maximum.ConvertUnit("m").Value, "stress_pa": stress.Maximum.ConvertUnit("Pa").Value}})
'''
        mechanical_result = json.loads(mechanical.run_python_script(mechanical_script, enable_logging=True, log_level="INFO"))
        expected_axial_m = source_force_n * length / (youngs * width * height)
        deformation_m = float(mechanical_result["deformation_m"])
        rel_error = abs(deformation_m - expected_axial_m) / expected_axial_m
        checks = {
            "maxwell_solved": em_solved, "force_parameter_created": bool(force_parameter),
            "force_is_finite_nonzero": math.isfinite(source_force_n) and source_force_n > 0,
            "mechanical_import": bool(mechanical_result["import_ok"]),
            "mechanical_solved": "Done" in mechanical_result["status"],
            "deformation_finite_positive": math.isfinite(deformation_m) and deformation_m > 0,
            "axial_theory_relative_error_lt_35pct": rel_error < 0.35,
        }
        transfer_file = case_dir / "force_transfer_contract.json"
        transfer = {"source": {"solver": "Maxwell 2D Magnetostatic", "design": "ForceSource", "quantity": "TransferForce.Force_x", "value_N": source_force_n}, "mapping": {"scale": 1.0, "target_component": "Mechanical Force.XComponent"}, "target": {"solver": "Mechanical 2026 R1 Static Structural", "analysis": "Maxwell Force Transfer", "applied_value_N": source_force_n}}
        write_json(transfer_file, transfer)
        result.update({
            "status": "PASS" if all(checks.values()) else "FAIL",
            "maxwell": {"solved": em_solved, "project_file": str(em_project), "force_quantities": quantities, "force_values": force_values, "solver_messages": em_messages},
            "transfer": transfer, "transfer_file": str(transfer_file),
            "mechanical": {"version": str(mechanical.version), "solution_status": mechanical_result["status"], "mesh": mesh, "maximum_total_deformation_m": deformation_m, "maximum_equivalent_stress_pa": float(mechanical_result["stress_pa"]), "axial_theory_deformation_m": expected_axial_m, "relative_error": rel_error},
            "checks": checks,
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    finally:
        if mechanical is not None:
            try:
                mechanical.exit(force=False)
                result["mechanical_normally_closed"] = not mechanical.is_alive
            except Exception as exc:
                result["mechanical_close_error"] = f"{type(exc).__name__}: {exc}"
        if maxwell is not None:
            try:
                result["release_return"] = maxwell.release_desktop(close_projects=True, close_desktop=True)
            except Exception as exc:
                result["release_error"] = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = cleanup_new_aedt_processes(baseline)
        result["processes_after_close"] = aedt_processes()
        write_json(case_dir / "result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
