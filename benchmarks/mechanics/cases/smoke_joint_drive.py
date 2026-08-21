"""PyMechanical prescribed revolute-joint rotation smoke test."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from datetime import datetime, timezone

from ansys.mechanical.core import launch_mechanical

from dynamics_smoke_common import AWP_ROOT261, MECH_EXE, OUT, ROOT, svg_plot, write_json


SPACECLAIM = AWP_ROOT261 + r"\scdm\SpaceClaim.exe"
GEOMETRY_SCRIPT = ROOT / "spaceclaim_single_link_geometry.py"
GEOMETRY = OUT / "joint_drive_link.scdocx"
RESULT = OUT / "joint_drive_results.json"
HISTORY = OUT / "joint_drive_history.csv"
PLOT = OUT / "joint_drive_response.svg"
LENGTH = 0.20
AMPLITUDE_DEG = 30.0
FREQUENCY_HZ = 1.0
END_TIME = 1.0
TIME_STEP = 0.05


def create_geometry() -> None:
    GEOMETRY.unlink(missing_ok=True)
    cmd=[SPACECLAIM,"/Headless=True","/Splash=False",f"/RunScript={GEOMETRY_SCRIPT}",f"/ScriptArgs={GEOMETRY}","/ScriptAPI=261","/ExitAfterScript=True"]
    done=subprocess.run(cmd,cwd=ROOT,check=False,timeout=180)
    if done.returncode or not GEOMETRY.is_file():
        raise RuntimeError("SpaceClaim single-link geometry failed")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for path in (RESULT,HISTORY,PLOT):
        path.unlink(missing_ok=True)
    print("=== PyMechanical prescribed joint-drive smoke test ===",flush=True)
    print("Python:",sys.executable,flush=True)
    create_geometry()
    mechanical=None
    try:
        mechanical=launch_mechanical(exec_file=MECH_EXE,batch=True,start_instance=True,cleanup_on_exit=True,loglevel="INFO",additional_envs={"AWP_ROOT261":AWP_ROOT261},verbose_mechanical=True)
        count=int(round(END_TIME/TIME_STEP))
        times=[i*TIME_STEP for i in range(count+1)]
        angles=[AMPLITUDE_DEG*math.sin(2*math.pi*FREQUENCY_HZ*t) for t in times]
        setup=f'''
import json
import math
from Ansys.Mechanical.DataModel import Enums
from Ansys.ACT.Interfaces.Common import SelectionTypeEnum
ExtAPI.DataModel.Project.New()
prefs=Ansys.ACT.Mechanical.Utilities.GeometryImportPreferences()
prefs.ProcessNamedSelections=False
prefs.ProcessMaterialProperties=False
prefs.ProcessCoordinateSystems=False
prefs.AnalysisType=Enums.GeometryImportPreference.AnalysisType.Type3D
gi=Model.GeometryImportGroup.AddGeometryImport()
gi.Import({str(GEOMETRY)!r},Enums.GeometryImportPreference.Format.Automatic,prefs)
body=Model.Geometry.GetChildren(Enums.DataModelObjectCategory.Body,True)[0]
body.Name="Driven rigid link"
body.Material="Structural Steel"
body.StiffnessBehavior=Enums.StiffnessBehavior.Rigid
def face_at(x):
    face=min(body.GetGeoBody().Faces,key=lambda f:abs(f.Centroid[0]-x))
    s=ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)
    s.Ids=[face.Id]
    return s
base=face_at(0.0)
tip=face_at({LENGTH})
cs=Model.CoordinateSystems.AddCoordinateSystem()
cs.Name="Driven hinge mobile frame"
cs.OriginDefineBy=Enums.CoordinateSystemAlignmentType.Associative
cs.OriginLocation=base
cs.PrimaryAxis=Enums.CoordinateSystemAxisType.PositiveXAxis
cs.PrimaryAxisDefineBy=Enums.CoordinateSystemAlignmentType.GlobalX
cs.SecondaryAxis=Enums.CoordinateSystemAxisType.PositiveYAxis
cs.SecondaryAxisDefineBy=Enums.CoordinateSystemAlignmentType.GlobalY
connections=Model.Connections if Model.Connections is not None else Model.AddConnections()
joint=connections.AddJoint()
joint.Name="Driven revolute joint"
joint.ConnectionType=Enums.JointScopingType.BodyToGround
joint.Type=Enums.JointType.Revolute
joint.MobileLocation=base
joint.ReferenceCoordinateSystem=Model.CoordinateSystems.Children[0]
joint.MobileCoordinateSystem=cs
analysis=Model.AddRigidDynamicsAnalysis()
analysis.Name="Prescribed sinusoidal joint rotation"
settings=analysis.AnalysisSettings
settings.SetStepEndTime(1,Quantity("{END_TIME} [s]"))
settings.SetTimeStep(1,Quantity("{TIME_STEP} [s]"))
drive=analysis.AddJointLoad()
drive.Name="Prescribed RZ rotation"
drive.Joint=joint
drive.JointConditionType=Enums.JointConditionType.Rotation
drive.Magnitude.Inputs[0].DiscreteValues=[Quantity(str(x)+" [s]") for x in {times!r}]
drive.Magnitude.Output.DiscreteValues=[Quantity(str(x)+" [deg]") for x in {angles!r}]
def position(name,location):
    p=analysis.Solution.AddPosition()
    p.Name=name
    p.LocationMethod=Enums.LocationDefinitionMethod.GeometrySelection
    p.GeometryLocation=location
    return p
p0=position("Base position",base)
p1=position("Tip position",tip)
pre_states=[[x.Name,str(x.ObjectState)] for x in [body,joint,analysis,drive,p0,p1]]
analysis.Solve(True)
status=str(analysis.Solution.Status)
messages=[[str(m.Severity),m.DisplayString] for m in ExtAPI.Application.Messages]
history=[]
if status=="Done":
    for t in {times[1:]!r}:
        p0.DisplayTime=Quantity(str(t)+" [s]")
        p1.DisplayTime=Quantity(str(t)+" [s]")
        analysis.Solution.EvaluateAllResults()
        def xyz(p): return [float(p.XAxis.ConvertUnit("m").Value),float(p.YAxis.ConvertUnit("m").Value),float(p.ZAxis.ConvertUnit("m").Value)]
        q0,q1=xyz(p0),xyz(p1)
        angle=math.atan2(q1[1]-q0[1],q1[0]-q0[0])
        history.append([float(t),angle,q0,q1])
json.dumps({{"status":status,"pre_states":pre_states,"messages":messages,"history":history,"drive_type":str(drive.JointConditionType),"drive_dof":str(drive.DOF),"joint_type":str(joint.Type)}})
'''
        payload=json.loads(mechanical.run_python_script(setup,enable_logging=True,log_level="INFO"))
        if payload["status"]!="Done":
            raise RuntimeError(f"Joint drive solve failed: {payload}")
        rows=[]
        previous_angle=previous_velocity=None
        for t,angle,q0,q1 in payload["history"]:
            target=math.radians(AMPLITUDE_DEG*math.sin(2*math.pi*FREQUENCY_HZ*t))
            velocity=0.0 if previous_angle is None else (angle-previous_angle)/TIME_STEP
            acceleration=0.0 if previous_velocity is None else (velocity-previous_velocity)/TIME_STEP
            rows.append({"time_s":t,"target_angle_deg":math.degrees(target),"ansys_angle_deg":math.degrees(angle),"angular_velocity_rad_s":velocity,"angular_acceleration_rad_s2":acceleration,"tip_x_m":q1[0],"tip_y_m":q1[1],"tip_z_m":q1[2]})
            previous_angle,previous_velocity=angle,velocity
        with HISTORY.open("w",newline="",encoding="utf-8") as file:
            writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        angle_error=max(abs(r["ansys_angle_deg"]-r["target_angle_deg"]) for r in rows)
        svg_plot(PLOT,[([r["time_s"] for r in rows],[r["ansys_angle_deg"] for r in rows],"Mechanical"),([r["time_s"] for r in rows],[r["target_angle_deg"] for r in rows],"Prescribed")],"Prescribed revolute-joint motion","Time (s)","Angle (deg)")
        checks={"solution_done":payload["status"]=="Done","native_revolute_joint":payload["joint_type"]=="Revolute","prescribed_rotation":payload["drive_type"]=="Rotation" and payload["drive_dof"]=="RotationZ","history_complete":len(rows)==count,"angle_tracks_drive":angle_error<0.5,"velocity_and_acceleration_finite":all(math.isfinite(r["angular_velocity_rad_s"]) and math.isfinite(r["angular_acceleration_rad_s2"]) for r in rows),"no_solver_errors":not any(m[0]=="Error" for m in payload["messages"])}
        result={"status":"PASS" if all(checks.values()) else "FAIL","timestamp_utc":datetime.now(timezone.utc).isoformat(),"analysis":"Mechanical Rigid Dynamics with prescribed Joint Rotation","model":{"link_length_m":LENGTH,"joint_type":"Revolute","drive_amplitude_deg":AMPLITUDE_DEG,"drive_frequency_hz":FREQUENCY_HZ,"end_time_s":END_TIME,"time_step_s":TIME_STEP},"results":{"sample_count":len(rows),"maximum_abs_angle_deg":max(abs(r["ansys_angle_deg"]) for r in rows),"maximum_abs_angular_velocity_rad_s":max(abs(r["angular_velocity_rad_s"]) for r in rows),"maximum_abs_angular_acceleration_rad_s2":max(abs(r["angular_acceleration_rad_s2"]) for r in rows),"maximum_angle_tracking_error_deg":angle_error},"mechanical":{"version":str(mechanical.version),"solution_status":payload["status"],"normally_closed":False},"checks":checks,"files":{"history_csv":str(HISTORY),"plot_svg":str(PLOT),"geometry":str(GEOMETRY)}}
        write_json(RESULT,result)
        print(json.dumps(result,indent=2),flush=True)
    finally:
        if mechanical is not None:
            mechanical.exit(force=False)
            if RESULT.exists():
                result=json.loads(RESULT.read_text(encoding="utf-8"));result["mechanical"]["normally_closed"]=True;write_json(RESULT,result)
            print("Mechanical alive after close:",mechanical.is_alive,flush=True)
    final=json.loads(RESULT.read_text(encoding="utf-8"))
    print("CASE B",final["status"],flush=True)
    return 0 if final["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
