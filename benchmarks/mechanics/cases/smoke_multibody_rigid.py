"""PyMechanical rigid-dynamics double-pendulum smoke test for Mechanical 261."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ansys.mechanical.core import launch_mechanical


ROOT = Path(__file__).resolve().parent
OUT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs"))
RESULT_JSON = OUT / "multibody_rigid_results.json"
HISTORY_CSV = OUT / "multibody_rigid_history.csv"
TRAJECTORY_SVG = OUT / "multibody_rigid_trajectory.svg"
ANGLE_SVG = OUT / "multibody_rigid_angles.svg"
NATIVE_GEOMETRY = OUT / "multibody_native_geometry.scdocx"
SPACECLAIM_SCRIPT = ROOT / "spaceclaim_multibody_geometry.py"

AWP_ROOT261 = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261"
MECH_EXE = AWP_ROOT261 + r"\aisol\bin\winx64\AnsysWBU.exe"
SPACECLAIM_EXE = AWP_ROOT261 + r"\scdm\SpaceClaim.exe"

L1 = 0.20
L2 = 0.20
WIDTH = 0.020
THICKNESS = 0.010
E = 200.0e9
NU = 0.30
DENSITY = 7850.0
GRAVITY = 9.80665
END_TIME = 0.50
TIME_STEP = 0.020


def run_spaceclaim_geometry() -> None:
    NATIVE_GEOMETRY.unlink(missing_ok=True)
    cmd = [SPACECLAIM_EXE, "/Headless=True", "/Splash=False", f"/RunScript={SPACECLAIM_SCRIPT}", f"/ScriptArgs={NATIVE_GEOMETRY}", "/ScriptAPI=261", "/ExitAfterScript=True"]
    print("SpaceClaim geometry:", subprocess.list2cmdline(cmd), flush=True)
    done = subprocess.run(cmd, cwd=ROOT, check=False, timeout=180)
    print("SpaceClaim exit code:", done.returncode, flush=True)
    if done.returncode or not NATIVE_GEOMETRY.is_file():
        raise RuntimeError("SpaceClaim did not create native geometry")


def svg_plot(path: Path, series: list[tuple[list[float], list[float], str]], title: str, xlabel: str, ylabel: str) -> None:
    width, height, margin = 760, 460, 58
    xs = [x for sx, _, _ in series for x in sx]
    ys = [y for _, sy, _ in series for y in sy]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    if xmax == xmin: xmax += 1.0
    if ymax == ymin: ymax += 1.0
    def px(x): return margin + (x-xmin)/(xmax-xmin)*(width-2*margin)
    def py(y): return height-margin-(y-ymin)/(ymax-ymin)*(height-2*margin)
    colors = ["#2563eb", "#dc2626", "#059669"]
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{width/2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>', f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="black"/>', f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="black"/>']
    for idx, (sx, sy, label) in enumerate(series):
        pts = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in zip(sx, sy))
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{colors[idx%len(colors)]}" stroke-width="2"/>')
        lines.append(f'<text x="{width-margin-160}" y="{margin+18*idx}" font-family="sans-serif" font-size="12" fill="{colors[idx%len(colors)]}">{label}</text>')
    lines += [f'<text x="{width/2}" y="{height-10}" text-anchor="middle" font-family="sans-serif">{xlabel}</text>', f'<text transform="translate(16,{height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif">{ylabel}</text>', '</svg>']
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for path in (RESULT_JSON, HISTORY_CSV, TRAJECTORY_SVG, ANGLE_SVG):
        path.unlink(missing_ok=True)
    print("=== PyMechanical rigid double-link smoke test ===", flush=True)
    print("Python:", sys.executable, flush=True)
    run_spaceclaim_geometry()
    mesh = {"node_count": 0, "element_count": 0, "note": "Rigid Dynamics uses native rigid bodies; no FE mesh is required"}
    mechanical = None
    closed = False
    payload = None
    try:
        mechanical = launch_mechanical(exec_file=MECH_EXE, batch=True, start_instance=True, cleanup_on_exit=True, loglevel="INFO", additional_envs={"AWP_ROOT261": AWP_ROOT261}, verbose_mechanical=True)
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
import_ok = gi.HasValidGeometry
bodies = Model.Geometry.GetChildren(Enums.DataModelObjectCategory.Body, True)
if len(bodies) != 2: raise RuntimeError("Expected 2 imported bodies, got %d" % len(bodies))
ordered = sorted(bodies, key=lambda b: b.GetGeoBody().Centroid[0])
for index, body in enumerate(ordered):
    body.Name = "Link%d" % (index+1)
    body.Material = "Structural Steel"
    body.StiffnessBehavior = Enums.StiffnessBehavior.Rigid
def face_selection(body, x_target):
    face = min(body.GetGeoBody().Faces, key=lambda f: abs(f.Centroid[0]-x_target))
    sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    sel.Ids = [face.Id]
    return sel
l1_base = face_selection(ordered[0], 0.0)
l1_end = face_selection(ordered[0], {L1})
l2_start = face_selection(ordered[1], {L1})
l2_tip = face_selection(ordered[1], {L1+L2})
# The touching CAD faces generate a redundant bonded contact.  Rigid Dynamics
# requires the kinematic connection to be represented by the revolute joint.
for contact in Model.Connections.GetChildren(Enums.DataModelObjectCategory.ContactRegion, True):
    contact.Delete()
def joint_cs(name, location):
    cs = Model.CoordinateSystems.AddCoordinateSystem()
    cs.Name = name
    cs.OriginDefineBy = Enums.CoordinateSystemAlignmentType.Associative
    cs.OriginLocation = location
    cs.PrimaryAxis = Enums.CoordinateSystemAxisType.PositiveXAxis
    # A Mechanical Revolute joint releases its local Z rotation.  Keep the
    # local frame aligned with the global frame so that the pendulum rotates
    # about global Z in the XY plane.
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
j1.Name = "Link1-Link2 revolute joint"
j1.ConnectionType = Enums.JointScopingType.BodyToBody
j1.Type = Enums.JointType.Revolute
j1.ReferenceLocation = l1_end
j1.MobileLocation = l2_start
j1.ReferenceCoordinateSystem = cs1r
j1.MobileCoordinateSystem = cs1m
analysis = Model.AddRigidDynamicsAnalysis()
analysis.Name = "Rigid double pendulum under gravity"
settings = analysis.AnalysisSettings
settings.SetStepEndTime(1, Quantity("{END_TIME} [s]"))
settings.SetTimeStep(1, Quantity("{TIME_STEP} [s]"))
gravity = analysis.AddEarthGravity()
gravity.Name = "Gravity -Y"
gravity.XComponent.Output.DiscreteValues = [Quantity("0 [m s^-2]")]
gravity.YComponent.Output.DiscreteValues = [Quantity("{-GRAVITY} [m s^-2]")]
gravity.ZComponent.Output.DiscreteValues = [Quantity("0 [m s^-2]")]
def position(name, ns):
    p = analysis.Solution.AddPosition()
    p.Name = name
    p.LocationMethod = Enums.LocationDefinitionMethod.GeometrySelection
    p.GeometryLocation = ns
    return p
p0 = position("Ground hinge position", l1_base)
p1 = position("Inter-link hinge position", l1_end)
p2 = position("Link2 tip position", l2_tip)
pre_states = [[x.Name,str(x.ObjectState)] for x in [j0,j1,gravity,analysis,p0,p1,p2]]
analysis.Solve(True)
solve_status = str(analysis.Solution.Status)
messages = [[str(m.Severity),m.DisplayString] for m in ExtAPI.Application.Messages]
times = [{','.join(f'{i*TIME_STEP:.12g}' for i in range(1, int(round(END_TIME/TIME_STEP))+1))}]
history = []
if solve_status == "Done":
    for t in times:
        for p in [p0,p1,p2]: p.DisplayTime = Quantity(str(t) + " [s]")
        analysis.Solution.EvaluateAllResults()
        def xyz(p): return [float(p.XAxis.ConvertUnit("m").Value),float(p.YAxis.ConvertUnit("m").Value),float(p.ZAxis.ConvertUnit("m").Value)]
        q0,q1,q2 = xyz(p0),xyz(p1),xyz(p2)
        a1 = math.atan2(q1[1]-q0[1],q1[0]-q0[0])
        a2 = math.atan2(q2[1]-q1[1],q2[0]-q1[0])
        history.append([float(t),a1,a2,q0,q1,q2])
json.dumps({{"import_ok":bool(import_ok),"solution_status":solve_status,"body_count":len(bodies),"joint_types":[str(j0.Type),str(j1.Type)],"pre_states":pre_states,"messages":messages,"history":history}})
'''
        payload = json.loads(mechanical.run_python_script(setup, enable_logging=True, log_level="INFO"))
        if payload["solution_status"] != "Done":
            raise RuntimeError("Rigid Dynamics solve rejected. States=%r Messages=%r" % (payload["pre_states"], payload["messages"]))
        history = payload["history"]
        rows = []
        for i, item in enumerate(history):
            t, a1, a2, q0, q1, q2 = item
            if i == 0:
                w1 = w2 = 0.0
            else:
                dt = t-history[i-1][0]
                w1, w2 = (a1-history[i-1][1])/dt, (a2-history[i-1][2])/dt
            rows.append([t, math.degrees(a1), math.degrees(a2), w1, w2, *q2])
        with HISTORY_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["time_s","link1_angle_deg","link2_angle_deg","link1_angular_velocity_rad_s","link2_angular_velocity_rad_s","tip_x_m","tip_y_m","tip_z_m"]); w.writerows(rows)
        times=[r[0] for r in rows]
        svg_plot(ANGLE_SVG, [(times,[r[1] for r in rows],"Link 1"),(times,[r[2] for r in rows],"Link 2")], "Rigid double pendulum angles", "Time (s)", "Angle (deg)")
        svg_plot(TRAJECTORY_SVG, [([r[5] for r in rows],[r[6] for r in rows],"Link 2 tip")], "Rigid Link 2 tip trajectory", "X (m)", "Y (m)")
        mass1=DENSITY*L1*WIDTH*THICKNESS; mass2=DENSITY*L2*WIDTH*THICKNESS
        checks={"solution_done":payload["solution_status"]=="Done","two_bodies":payload["body_count"]==2,"two_revolute_joints":payload["joint_types"]==["Revolute","Revolute"],"history_complete":len(rows)==int(round(END_TIME/TIME_STEP)),"gravity_produced_motion":max(abs(r[1]) for r in rows)>1.0 and max(abs(r[2]) for r in rows)>1.0,"ground_drift_small":max(math.sqrt(sum(v*v for v in h[3])) for h in history)<1e-6,"finite_history":all(math.isfinite(v) for r in rows for v in r)}
        result={"status":"PASS" if all(checks.values()) else "FAIL","timestamp_utc":datetime.now(timezone.utc).isoformat(),"mechanical":{"version":str(mechanical.version),"product_version":mechanical.run_python_script("ExtAPI.DataModel.Project.ProductVersion"),"solution_status":payload["solution_status"],"normally_closed":False},"method":"Mechanical Rigid Dynamics with two native SpaceClaim rigid bodies and native revolute joints","model":{"link1_length_m":L1,"link2_length_m":L2,"width_m":WIDTH,"thickness_m":THICKNESS,"density_kg_m3":DENSITY,"link1_mass_kg":mass1,"link2_mass_kg":mass2,"link1_inertia_z_kg_m2":mass1*(L1*L1+WIDTH*WIDTH)/12,"link2_inertia_z_kg_m2":mass2*(L2*L2+WIDTH*WIDTH)/12,"gravity_m_s2":GRAVITY,"joint_types":payload["joint_types"],"end_time_s":END_TIME,"time_step_s":TIME_STEP},"mesh":mesh,"results":{"sample_count":len(rows),"maximum_abs_link1_angle_deg":max(abs(r[1]) for r in rows),"maximum_abs_link2_angle_deg":max(abs(r[2]) for r in rows),"maximum_abs_link1_angular_velocity_rad_s":max(abs(r[3]) for r in rows),"maximum_abs_link2_angular_velocity_rad_s":max(abs(r[4]) for r in rows),"final_tip_position_m":rows[-1][5:8]},"checks":checks,"files":{"history_csv":str(HISTORY_CSV),"angle_plot_svg":str(ANGLE_SVG),"trajectory_plot_svg":str(TRAJECTORY_SVG),"native_geometry":str(NATIVE_GEOMETRY)}}
        RESULT_JSON.write_text(json.dumps(result,indent=2),encoding="utf-8")
        print(json.dumps(result,indent=2), flush=True)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", flush=True)
        return 1
    finally:
        if mechanical is not None:
            print("Closing Mechanical normally", flush=True)
            mechanical.exit(force=False); closed=True
            print("Mechanical alive after close:", mechanical.is_alive, flush=True)
        if RESULT_JSON.exists() and closed:
            data=json.loads(RESULT_JSON.read_text(encoding="utf-8")); data["mechanical"]["normally_closed"]=True; RESULT_JSON.write_text(json.dumps(data,indent=2),encoding="utf-8")
    final=json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    print("CASE A", final["status"], flush=True)
    return 0 if final["status"]=="PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
