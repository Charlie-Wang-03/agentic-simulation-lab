"""Case E: translating piston transfers momentum into a native SPH free surface."""

from pathlib import Path
import json
import math
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, read_sph_steps


OUT=OUTPUT_ROOT/"case_e_moving_boundary"; OUT.mkdir(parents=True,exist_ok=True); RESULT=OUT/"result.json"
result={"case":"E","status":"FAIL","stage":"initializing"}
try:
    project=app.CreateProject(); study=project.GetStudy(); study.SetName("Case E - SPH Translating Piston")
    project_path=OUT/"case_e_moving_boundary.rocky"; project.SaveProject(str(project_path))
    sph,water,physics=configure_water_sph(study,size_m=0.01,solver_model="IISPH")
    tank,_=import_open_tank(study,asset="sph_hydro_tank.stl")
    paddle=study.ImportWall(str(ASSET_ROOT/"sph_piston.stl"))[0]; paddle.SetName("Translating Piston"); paddle.SetSphBoundaryType("no_slip_laminar")
    module=study.GetModuleCollection().GetModule("SPH Boundary Interaction Statistics"); module.EnableModule()
    add_sph_volume(study,name="Paddle Water",center_m=(0.0,0.0,0.035),dimensions_m=(0.06,0.04,0.06),sph_size_m=0.01)
    piston_speed=0.15; frame=study.GetMotionFrameSource().NewFrame(); frame.SetName("Driven Piston")
    frame.AddTranslationMotion(start_time=(0.30,"s"),stop_time=(0.50,"s"),velocity=((piston_speed,0.0,0.0),"m/s")); frame.ApplyTo(paddle)
    set_domain(study); simulation_ok=solve(study,project,project_path,duration_s=0.65,output_dt_s=0.025)
    metadata=export_lagrangian(study,OUT/"sph_lagrangian.csv"); steps,_=read_sph_steps(study)
    history=[]
    for t,rows in steps:
        kinetic=sum(0.5*float(r["mass_kg"])*(float(r["velocity_x_m_per_s"])**2+float(r["velocity_y_m_per_s"])**2+float(r["velocity_z_m_per_s"])**2) for r in rows)
        mean_speed=sum(math.sqrt(float(r["velocity_x_m_per_s"])**2+float(r["velocity_y_m_per_s"])**2+float(r["velocity_z_m_per_s"])**2) for r in rows)/max(len(rows),1)
        surface=max((float(r["position_z_m"])+0.005 for r in rows),default=math.nan)
        horizontal_ke=sum(0.5*float(r["mass_kg"])*(float(r["velocity_x_m_per_s"])**2+float(r["velocity_y_m_per_s"])**2) for r in rows)
        momentum_x=sum(float(r["mass_kg"])*float(r["velocity_x_m_per_s"]) for r in rows)
        history.append({"time_s":t,"kinetic_energy_j":kinetic,"horizontal_kinetic_energy_j":horizontal_ke,"momentum_x_kg_m_per_s":momentum_x,"mean_speed_m_per_s":mean_speed,"free_surface_height_m":surface})
    pre=[x["horizontal_kinetic_energy_j"] for x in history if 0.25<=x["time_s"]<=0.30]; driven=[x["horizontal_kinetic_energy_j"] for x in history if 0.325<=x["time_s"]<=0.50]
    reaction_force=[]
    for left,right in zip(history,history[1:]):
        dt=right["time_s"]-left["time_s"]
        reaction_force.append({"time_s":right["time_s"],"fluid_force_x_n":(right["momentum_x_kg_m_per_s"]-left["momentum_x_kg_m_per_s"])/dt,"body_reaction_x_n":-(right["momentum_x_kg_m_per_s"]-left["momentum_x_kg_m_per_s"])/dt})
    curve_names=list(paddle.GetCurveNames()); curves={}
    for name in curve_names:
        if any(token in name.lower() for token in ("force","moment","torque","pressure")):
            try:
                ts,vs=paddle.GetNumpyCurve(name); curves[name]=[{"time_s":float(t),"value":float(v)} for t,v in zip(ts,vs)]
            except Exception as exc: curves[name]={"error":repr(exc)}
    driven_forces=[abs(x["body_reaction_x_n"]) for x in reaction_force if 0.325<=x["time_s"]<=0.525]
    checks={"solver_advanced":simulation_ok,"horizontal_kinetic_energy_increases":max(driven,default=0.0)>1.25*max(pre,default=1e-30),"fluid_velocity_nonzero":max((x["mean_speed_m_per_s"] for x in history),default=0.0)>0.05,"free_surface_deforms":max((x["free_surface_height_m"] for x in history),default=0.0)-min((x["free_surface_height_m"] for x in history),default=0.0)>0.005,"momentum_reaction_force_nonzero":max(driven_forces,default=0.0)>0.001}
    result.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"piston_speed_m_per_s":piston_speed,"history":history,"momentum_balance_reaction_force":reaction_force,"paddle_curve_names":curve_names,"paddle_force_torque_curves":curves,"metadata":metadata,"project":str(project_path)})
except Exception:
    result["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    try: app.Exit()
    except Exception: pass
