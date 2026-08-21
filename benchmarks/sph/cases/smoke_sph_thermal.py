"""Case G: hot native SPH liquid cooling against a prescribed cold wall."""

from pathlib import Path
import json
import math
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, read_sph_steps


OUT=OUTPUT_ROOT/"case_g_thermal"; OUT.mkdir(parents=True,exist_ok=True); RESULT=OUT/"result.json"
result={"case":"G","status":"FAIL","stage":"initializing"}
try:
    project=app.CreateProject(); study=project.GetStudy(); study.SetName("Case G - SPH Hot Liquid Cold Wall")
    project_path=OUT/"case_g_thermal.rocky"; project.SaveProject(str(project_path))
    sph,water,physics=configure_water_sph(study,size_m=0.01,solver_model="IISPH",thermal=True)
    physics.SetSphThermalTransferModel("cleary")
    tank,boundary_values=import_open_tank(study,asset="sph_hydro_tank.stl")
    tank.SetThermalBoundaryConditionType("prescribed_temperature"); tank.SetTemperature(293.15,"K")
    add_sph_volume(study,name="Hot Water",center_m=(0.0,0.0,0.035),dimensions_m=(0.06,0.04,0.06),sph_size_m=0.01,temperature_k=353.15)
    set_domain(study); simulation_ok=solve(study,project,project_path,duration_s=0.60,output_dt_s=0.05)
    metadata=export_lagrangian(study,OUT/"sph_lagrangian.csv"); steps,_=read_sph_steps(study)
    history=[]
    for t,rows in steps:
        mass=sum(float(r["mass_kg"]) for r in rows); mean_temp=sum(float(r["mass_kg"])*float(r["temperature_k"]) for r in rows)/max(mass,1e-30)
        energy=mass*4182.0*mean_temp
        history.append({"time_s":t,"mass_kg":mass,"mean_temperature_k":mean_temp,"fluid_internal_energy_j":energy})
    heat_rates=[]
    for left,right in zip(history,history[1:]):
        dt=right["time_s"]-left["time_s"]; q=-(right["fluid_internal_energy_j"]-left["fluid_internal_energy_j"])/dt
        heat_rates.append({"time_s":right["time_s"],"wall_heat_removal_rate_w":q})
    delta_u=history[-1]["fluid_internal_energy_j"]-history[0]["fluid_internal_energy_j"] if history else math.nan
    integrated_q=sum(item["wall_heat_removal_rate_w"]*(history[i+1]["time_s"]-history[i]["time_s"]) for i,item in enumerate(heat_rates))
    balance=abs(delta_u+integrated_q)/max(abs(delta_u),1.0)
    temps=[x["mean_temperature_k"] for x in history]
    checks={"solver_advanced":simulation_ok,"temperature_field_exported":"temperature_k" in metadata["selected_fields"],"liquid_cools":temps[-1]<temps[0]-0.01 if temps else False,"temperature_bounded":min(temps)>=293.15-1.0 and max(temps)<=353.15+1.0 if temps else False,"energy_balance_lt_1pct":balance<0.01,"finite_heat_rate":finite([x["wall_heat_removal_rate_w"] for x in heat_rates])}
    result.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"cold_wall_temperature_k":293.15,"initial_liquid_temperature_k":353.15,"history":history,"wall_heat_rate":heat_rates,"fluid_energy_change_j":delta_u,"integrated_wall_heat_removal_j":integrated_q,"relative_energy_balance_error":balance,"metadata":metadata,"project":str(project_path)})
except Exception:
    result["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    try: app.Exit()
    except Exception: pass
