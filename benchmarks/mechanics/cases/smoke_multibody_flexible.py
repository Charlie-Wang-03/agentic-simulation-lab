"""PyMechanical rigid-flexible double-link transient smoke test for Mechanical 261."""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone

from ansys.mechanical.core import launch_mechanical

from smoke_multibody_rigid import (
    AWP_ROOT261,
    DENSITY,
    GRAVITY,
    L1,
    L2,
    MECH_EXE,
    NATIVE_GEOMETRY,
    NU,
    OUT,
    ROOT,
    THICKNESS,
    WIDTH,
    E,
    run_spaceclaim_geometry,
    svg_plot,
)


RESULT_JSON = OUT / "multibody_flexible_results.json"
HISTORY_CSV = OUT / "multibody_flexible_history.csv"
TRAJECTORY_SVG = OUT / "multibody_flexible_trajectory.svg"
DEFORMATION_SVG = OUT / "multibody_flexible_deformation.svg"
STRESS_SVG = OUT / "multibody_flexible_stress.svg"

ELEMENT_SIZE = 0.020
END_TIME = 0.20
TIME_STEP = 0.020


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for path in (RESULT_JSON, HISTORY_CSV, TRAJECTORY_SVG, DEFORMATION_SVG, STRESS_SVG):
        path.unlink(missing_ok=True)
    print("=== PyMechanical rigid-flexible double-link smoke test ===", flush=True)
    print("Python:", sys.executable, flush=True)
    run_spaceclaim_geometry()

    mechanical = None
    closed = False
    try:
        mechanical = launch_mechanical(
            exec_file=MECH_EXE,
            batch=True,
            start_instance=True,
            cleanup_on_exit=True,
            loglevel="INFO",
            additional_envs={"AWP_ROOT261": AWP_ROOT261},
            verbose_mechanical=True,
        )
        print(f"Connected to Mechanical {mechanical.version}", flush=True)
        setup = f'''
import json
import math
from Ansys.Mechanical.DataModel import Enums
from Ansys.ACT.Interfaces.Common import SelectionTypeEnum
ExtAPI.DataModel.Project.New()
prefs = Ansys.ACT.Mechanical.Utilities.GeometryImportPreferences()
prefs.ProcessNamedSelections = False
prefs.ProcessMaterialProperties = False
prefs.ProcessCoordinateSystems = False
prefs.AnalysisType = Enums.GeometryImportPreference.AnalysisType.Type3D
gi = Model.GeometryImportGroup.AddGeometryImport()
gi.Import({str(NATIVE_GEOMETRY)!r}, Enums.GeometryImportPreference.Format.Automatic, prefs)
bodies = Model.Geometry.GetChildren(Enums.DataModelObjectCategory.Body, True)
if len(bodies) != 2: raise RuntimeError("Expected 2 imported bodies, got %d" % len(bodies))
ordered = sorted(bodies, key=lambda b: b.GetGeoBody().Centroid[0])
ordered[0].Name = "Rigid Link 1"
ordered[0].Material = "Structural Steel"
ordered[0].StiffnessBehavior = Enums.StiffnessBehavior.Rigid
ordered[1].Name = "Flexible Link 2"
ordered[1].Material = "Structural Steel"
ordered[1].StiffnessBehavior = Enums.StiffnessBehavior.Flexible
def face_selection(body, x_target):
    face = min(body.GetGeoBody().Faces, key=lambda f: abs(f.Centroid[0]-x_target))
    sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    sel.Ids = [face.Id]
    return sel
def vertex_selection(body, x_target):
    vertex = min(body.GetGeoBody().Vertices, key=lambda v: abs(v.X-x_target) + abs(v.Y+{WIDTH/2}) + abs(v.Z+{THICKNESS/2}))
    sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    sel.Ids = [vertex.Id]
    return sel
def body_selection(body):
    sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    sel.Ids = [body.GetGeoBody().Id]
    return sel
l1_base = face_selection(ordered[0], 0.0)
l1_end = face_selection(ordered[0], {L1})
l2_start = face_selection(ordered[1], {L1})
l2_tip = face_selection(ordered[1], {L1+L2})
p0_point = vertex_selection(ordered[0], 0.0)
p1_point = vertex_selection(ordered[0], {L1})
p2_point = vertex_selection(ordered[1], {L1+L2})
l2_body = body_selection(ordered[1])
for contact in Model.Connections.GetChildren(Enums.DataModelObjectCategory.ContactRegion, True):
    contact.Delete()
def joint_cs(name, location):
    cs = Model.CoordinateSystems.AddCoordinateSystem()
    cs.Name = name
    cs.OriginDefineBy = Enums.CoordinateSystemAlignmentType.Associative
    cs.OriginLocation = location
    cs.PrimaryAxis = Enums.CoordinateSystemAxisType.PositiveXAxis
    cs.PrimaryAxisDefineBy = Enums.CoordinateSystemAlignmentType.GlobalX
    cs.SecondaryAxis = Enums.CoordinateSystemAxisType.PositiveYAxis
    cs.SecondaryAxisDefineBy = Enums.CoordinateSystemAlignmentType.GlobalY
    return cs
cs0m = joint_cs("Ground hinge mobile axis Z", l1_base)
cs1r = joint_cs("Inter-link reference axis Z", l1_end)
cs1m = joint_cs("Inter-link mobile axis Z", l2_start)
j0 = Model.Connections.AddJoint()
j0.Name = "Ground revolute joint"
j0.ConnectionType = Enums.JointScopingType.BodyToGround
j0.Type = Enums.JointType.Revolute
j0.MobileLocation = l1_base
j0.ReferenceCoordinateSystem = Model.CoordinateSystems.Children[0]
j0.MobileCoordinateSystem = cs0m
j1 = Model.Connections.AddJoint()
j1.Name = "Rigid-flexible revolute joint"
j1.ConnectionType = Enums.JointScopingType.BodyToBody
j1.Type = Enums.JointType.Revolute
j1.ReferenceLocation = l1_end
j1.MobileLocation = l2_start
j1.ReferenceCoordinateSystem = cs1r
j1.MobileCoordinateSystem = cs1m
Model.Mesh.ElementSize = Quantity("{ELEMENT_SIZE} [m]")
Model.Mesh.GenerateMesh()
mesh_data = ExtAPI.DataModel.MeshDataByName("Global")
node_count = mesh_data.Nodes.Count
element_count = mesh_data.Elements.Count
analysis = Model.AddTransientStructuralAnalysis()
analysis.Name = "Rigid-flexible double pendulum under gravity"
settings = analysis.AnalysisSettings
settings.LargeDeflection = True
settings.SetStepEndTime(1, Quantity("{END_TIME} [s]"))
settings.SetInitialTimeStep(1, Quantity("{TIME_STEP} [s]"))
settings.SetMinimumTimeStep(1, Quantity("{TIME_STEP/4} [s]"))
settings.SetMaximumTimeStep(1, Quantity("{TIME_STEP} [s]"))
gravity = analysis.AddEarthGravity()
gravity.Name = "Gravity -Y"
gravity.XComponent.Output.DiscreteValues = [Quantity("0 [m s^-2]")]
gravity.YComponent.Output.DiscreteValues = [Quantity("{-GRAVITY} [m s^-2]")]
gravity.ZComponent.Output.DiscreteValues = [Quantity("0 [m s^-2]")]
def displacement(name, location, component):
    result = analysis.Solution.AddDirectionalDeformation()
    result.Name = name
    result.Location = location
    result.NormalOrientation = component
    return result
def displacement_triplet(name, location):
    return [displacement(name+" X",location,Enums.NormalOrientationType.XAxis),displacement(name+" Y",location,Enums.NormalOrientationType.YAxis),displacement(name+" Z",location,Enums.NormalOrientationType.ZAxis)]
u0 = displacement_triplet("Ground hinge displacement", p0_point)
u2 = displacement_triplet("Flexible Link 2 tip displacement", p2_point)
deformation = analysis.Solution.AddTotalDeformation()
deformation.Name = "Flexible Link 2 total deformation"
deformation.Location = l2_body
stress = analysis.Solution.AddEquivalentStress()
stress.Name = "Flexible Link 2 equivalent stress"
stress.Location = l2_body
pre_states = [[x.Name,str(x.ObjectState)] for x in [ordered[0],ordered[1],j0,j1,gravity,analysis]+u0+u2+[deformation,stress]]
analysis.Solve(True)
solve_status = str(analysis.Solution.Status)
messages = [[str(m.Severity),m.DisplayString] for m in ExtAPI.Application.Messages]
times = [{','.join(f'{i*TIME_STEP:.12g}' for i in range(1, int(round(END_TIME/TIME_STEP))+1))}]
history = []
if solve_status == "Done":
    for t in times:
        for result in u0+u2+[deformation,stress]: result.DisplayTime = Quantity(str(t) + " [s]")
        analysis.Solution.EvaluateAllResults()
        def xyz(u, initial): return [initial[i]+float(u[i].Maximum.ConvertUnit("m").Value) for i in range(3)]
        # A rigid body's deformation result is reported at its pilot/reference
        # node (the initial centroid here).  Reconstruct the hinged end from
        # that centroid motion and the exact rigid-link geometry.
        c1 = xyz(u0,[{L1/2},0.0,0.0])
        q0 = [0.0,0.0,0.0]
        q1 = [2.0*c1[0],2.0*c1[1],2.0*c1[2]]
        q2 = xyz(u2,[{L1+L2},{-WIDTH/2},{-THICKNESS/2}])
        a1 = math.atan2(q1[1]-q0[1],q1[0]-q0[0])
        a2 = math.atan2(q2[1]-q1[1],q2[0]-q1[0])
        history.append([float(t),a1,a2,q0,q1,q2,float(deformation.Maximum.ConvertUnit("m").Value),float(stress.Maximum.ConvertUnit("Pa").Value)])
json.dumps({{"import_ok":bool(gi.HasValidGeometry),"solution_status":solve_status,"body_count":len(bodies),"joint_types":[str(j0.Type),str(j1.Type)],"body_behaviors":[str(ordered[0].StiffnessBehavior),str(ordered[1].StiffnessBehavior)],"body_masses_kg":[float(b.Mass.ConvertUnit("kg").Value) for b in ordered],"node_count":int(node_count),"element_count":int(element_count),"pre_states":pre_states,"messages":messages,"history":history}})
'''
        payload = json.loads(mechanical.run_python_script(setup, enable_logging=True, log_level="INFO"))
        if payload["solution_status"] != "Done":
            raise RuntimeError("Transient Structural solve failed. States=%r Messages=%r" % (payload["pre_states"], payload["messages"]))

        history = payload["history"]
        rows = []
        for i, item in enumerate(history):
            t, a1, a2, q0, q1, q2, dmax, smax = item
            if i == 0:
                w1 = w2 = 0.0
            else:
                dt = t - history[i-1][0]
                w1 = (a1-history[i-1][1])/dt
                w2 = (a2-history[i-1][2])/dt
            rows.append([t, math.degrees(a1), math.degrees(a2), w1, w2, *q2, dmax, smax])
        with HISTORY_CSV.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["time_s","link1_angle_deg","link2_chord_angle_deg","link1_angular_velocity_rad_s","link2_chord_angular_velocity_rad_s","tip_x_m","tip_y_m","tip_z_m","link2_max_total_deformation_m","link2_max_equivalent_stress_pa"])
            writer.writerows(rows)
        times = [r[0] for r in rows]
        svg_plot(TRAJECTORY_SVG, [([r[5] for r in rows],[r[6] for r in rows],"Flexible Link 2 tip")], "Rigid-flexible tip trajectory", "X (m)", "Y (m)")
        svg_plot(DEFORMATION_SVG, [(times,[1000*r[8] for r in rows],"Link 2")], "Flexible Link 2 total deformation", "Time (s)", "Maximum (mm)")
        svg_plot(STRESS_SVG, [(times,[r[9]/1e6 for r in rows],"Link 2")], "Flexible Link 2 equivalent stress", "Time (s)", "Maximum (MPa)")
        checks = {
            "solution_done": payload["solution_status"] == "Done",
            "rigid_and_flexible_bodies": payload["body_behaviors"] == ["Rigid","Flexible"],
            "two_revolute_joints": payload["joint_types"] == ["Revolute","Revolute"],
            "mesh_created": payload["node_count"] > 0 and payload["element_count"] > 0,
            "history_complete": len(rows) == int(round(END_TIME/TIME_STEP)),
            "rigid_motion_present": max(abs(r[1]) for r in rows) > 1.0,
            "flexible_motion_present": max(abs(r[2]) for r in rows) > 1.0,
            "deformation_positive_finite": max(r[8] for r in rows) > 0.0 and all(math.isfinite(r[8]) for r in rows),
            "stress_positive_finite": max(r[9] for r in rows) > 0.0 and all(math.isfinite(r[9]) for r in rows),
            "ground_drift_small": max(math.sqrt(sum(v*v for v in h[3])) for h in history) < 1e-6,
            "no_solver_errors": not any(m[0] == "Error" for m in payload["messages"]),
            "finite_history": all(math.isfinite(v) for r in rows for v in r),
        }
        result = {
            "status":"PASS" if all(checks.values()) else "FAIL",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "mechanical":{"version":str(mechanical.version),"product_version":mechanical.run_python_script("ExtAPI.DataModel.Project.ProductVersion"),"solution_status":payload["solution_status"],"normally_closed":False},
            "method":"Mechanical Transient Structural rigid-flexible coupling with native revolute joints and large deflection",
            "model":{"link1_length_m":L1,"link2_length_m":L2,"width_m":WIDTH,"thickness_m":THICKNESS,"youngs_modulus_pa":E,"poisson_ratio":NU,"density_kg_m3":DENSITY,"body_masses_kg":payload["body_masses_kg"],"gravity_m_s2":GRAVITY,"joint_types":payload["joint_types"],"body_behaviors":payload["body_behaviors"],"end_time_s":END_TIME,"time_step_s":TIME_STEP},
            "mesh":{"nominal_element_size_m":ELEMENT_SIZE,"node_count":payload["node_count"],"element_count":payload["element_count"]},
            "results":{"sample_count":len(rows),"maximum_abs_link1_angle_deg":max(abs(r[1]) for r in rows),"maximum_abs_link2_chord_angle_deg":max(abs(r[2]) for r in rows),"maximum_abs_link1_angular_velocity_rad_s":max(abs(r[3]) for r in rows),"maximum_abs_link2_angular_velocity_rad_s":max(abs(r[4]) for r in rows),"maximum_link2_total_deformation_m":max(r[8] for r in rows),"maximum_link2_total_deformation_mm":1000*max(r[8] for r in rows),"maximum_link2_equivalent_stress_pa":max(r[9] for r in rows),"maximum_link2_equivalent_stress_mpa":max(r[9] for r in rows)/1e6,"final_tip_position_m":rows[-1][5:8]},
            "checks":checks,
            "files":{"history_csv":str(HISTORY_CSV),"trajectory_plot_svg":str(TRAJECTORY_SVG),"deformation_plot_svg":str(DEFORMATION_SVG),"stress_plot_svg":str(STRESS_SVG),"native_geometry":str(NATIVE_GEOMETRY)},
        }
        RESULT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", flush=True)
        return 1
    finally:
        if mechanical is not None:
            print("Closing Mechanical normally", flush=True)
            mechanical.exit(force=False)
            closed = True
            print("Mechanical alive after close:", mechanical.is_alive, flush=True)
        if RESULT_JSON.exists() and closed:
            data = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
            data["mechanical"]["normally_closed"] = True
            RESULT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    final = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    print("CASE B", final["status"], flush=True)
    return 0 if final["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
