"""Case H: free rigid plate falls into a native SPH free surface."""

from pathlib import Path
import json
import math
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, read_sph_steps


OUT=OUTPUT_ROOT/"case_h_rigid_body"; OUT.mkdir(parents=True,exist_ok=True); RESULT=OUT/"result.json"
result={"case":"H","status":"FAIL","stage":"initializing"}
try:
    project=app.CreateProject(); study=project.GetStudy(); study.SetName("Case H - Rigid Plate Water Entry")
    project_path=OUT/"case_h_rigid_body.rocky"; project.SaveProject(str(project_path))
    sph,water,physics=configure_water_sph(study,size_m=0.01,solver_model="IISPH")
    tank,_=import_open_tank(study,asset="sph_hydro_tank.stl")
    add_sph_volume(study,name="Impact Water",center_m=(0.0,0.0,0.035),dimensions_m=(0.06,0.04,0.06),sph_size_m=0.01)
    body=study.ImportWall(str(ASSET_ROOT/"hopper_gate.stl"))[0]; body.SetName("Falling Rigid Plate")
    body.SetTranslation((0.0,0.0,0.065),"m"); body.SetBoundaryMass(0.020,"kg"); body.SetSphBoundaryType("no_slip_laminar")
    body.SetPrincipalMomentOfInertia((8.34e-6,8.34e-6,1.67e-5),"kg.m2")
    module=study.GetModuleCollection().GetModule("SPH Boundary Interaction Statistics"); module.EnableModule()
    study.GetSimulatorRun().EnableFEMForces()
    frame=study.GetMotionFrameSource().NewFrame(); frame.SetName("Free Falling Body"); frame.SetRelativePosition((0.0,0.0,0.084),"m")
    frame.AddFreeBodyTranslationMotion("z"); frame.ApplyTo(body)
    set_domain(study); simulation_ok=solve(study,project,project_path,duration_s=0.60,output_dt_s=0.02)
    metadata=export_lagrangian(study,OUT/"sph_lagrangian.csv"); steps,_=read_sph_steps(study)
    try: grid_names=list(frame.GetGridFunctionNames())
    except Exception: grid_names=[]
    frame_fields={}
    time_set=study.GetTimeSet(); time_steps=list(time_set.GetTimeSteps()); times=[float(v) for v in time_set.GetValues("s")]
    for name in grid_names:
        if any(token in name.lower() for token in ("coordinate","position","velocity","acceleration","force")):
            try:
                gf=frame.GetGridFunction(name); series=[]
                for t,step in zip(times,time_steps):
                    gf.SetCurrentTimeStep(step); a=gf.GetArray(); vals=[] if a is None else a.tolist(); series.append({"time_s":t,"values":[float(v) for v in vals]})
                frame_fields[name]=series
            except Exception as exc: frame_fields[name]={"error":repr(exc)}
    curve_names=list(body.GetCurveNames()); frame_curve_names=list(frame.GetCurveNames()); curves={}
    for owner,prefix,names in ((body,"body",curve_names),(frame,"frame",frame_curve_names)):
      for name in names:
        if any(token in name.lower() for token in ("force","velocity","position","translation")):
            try:
                ts,vs=owner.GetNumpyCurve(name); curves[f"{prefix}:{name}"]=[{"time_s":float(t),"value":float(v)} for t,v in zip(ts,vs)]
            except Exception as exc: curves[f"{prefix}:{name}"]={"error":repr(exc)}
    fluid_surface=[]
    for t,rows in steps:
        pressures=[float(r["pressure_pa"]) for r in rows if math.isfinite(float(r["pressure_pa"]))]
        fluid_surface.append({"time_s":t,"surface_m":max((float(r["position_z_m"])+0.005 for r in rows),default=math.nan),"max_pressure_pa":max(pressures,default=math.nan)})
    z_candidates=[series for name,series in frame_fields.items() if isinstance(series,list) and ("coordinate" in name.lower() or "position" in name.lower()) and (name.lower().endswith("z") or " : z" in name.lower())]
    z_values=[item["values"][0] for series in z_candidates for item in series if item["values"]]
    for name,series in curves.items():
        if isinstance(series,list) and ("position" in name.lower() or "translation" in name.lower()) and (name.lower().endswith("z") or " : z" in name.lower()):
            z_values.extend(item["value"] for item in series)
    force_series=[series for name,series in curves.items() if "force" in name.lower() and isinstance(series,list)]
    force_values=[abs(item["value"]) for series in force_series for item in series if math.isfinite(item["value"])]
    force_evidence=bool(force_series)
    finite_pressures=[x["max_pressure_pa"] for x in fluid_surface if math.isfinite(x["max_pressure_pa"])]
    checks={"solver_advanced":simulation_ok,"fluid_fields":metadata["row_count"]>0,"rigid_body_state_api":bool(frame_fields or curves),"body_moves":max(z_values)-min(z_values)>0.001 if z_values else False,"impact_pressure_positive":max(finite_pressures,default=0.0)>0.0,"fluid_to_body_force_api":force_evidence,"force_history_finite":finite(force_values)}
    result.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"body_mass_kg":0.020,"frame_grid_function_names":grid_names,"body_curve_names":curve_names,"frame_curve_names":frame_curve_names,"rigid_body_fields":frame_fields,"body_curves":curves,"fluid_history":fluid_surface,"metadata":metadata,"project":str(project_path)})
except Exception:
    result["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    try: app.Exit()
    except Exception: pass
