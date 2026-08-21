"""Case J: native SPH coarse/medium/fine dam-break sensitivity."""

from pathlib import Path
import json
import math
import time
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, read_sph_steps


OUT=OUTPUT_ROOT/"case_j_resolution"; OUT.mkdir(parents=True,exist_ok=True); RESULT=OUT/"result.json"
result={"case":"J","status":"FAIL","stage":"initializing"}
try:
    runs={}
    for label,size in (("coarse",0.015),("medium",0.010),("fine",0.0075)):
        project=app.CreateProject(); study=project.GetStudy(); study.SetName(f"Case J - {label} SPH")
        run_dir=OUT/label; run_dir.mkdir(parents=True,exist_ok=True); project_path=run_dir/f"{label}.rocky"; project.SaveProject(str(project_path))
        sph,water,physics=configure_water_sph(study,size_m=size,solver_model="IISPH")
        tank,_=import_open_tank(study)
        add_sph_volume(study,name=f"{label} Dam Column",center_m=(-0.115,0.0,0.045),dimensions_m=(0.06,0.04,0.08),sph_size_m=size)
        set_domain(study); started=time.perf_counter(); simulation_ok=solve(study,project,project_path,duration_s=0.25,output_dt_s=0.05); runtime=time.perf_counter()-started
        metadata=export_lagrangian(study,run_dir/"sph_lagrangian.csv"); steps,_=read_sph_steps(study)
        history=[{"time_s":t,"front_x_m":max((float(r["position_x_m"])+0.5*size for r in rows),default=math.nan),"mass_kg":sum(float(r["mass_kg"]) for r in rows)} for t,rows in steps]
        masses=[x["mass_kg"] for x in history]; drift=(max(masses)-min(masses))/max(masses[0],1e-30) if masses else math.inf
        observation=min(history,key=lambda x:abs(x["time_s"]-0.20))
        runs[label]={"element_size_m":size,"element_count":metadata["element_counts"][-1] if metadata["element_counts"] else 0,"runtime_s":runtime,"front_at_0p2_s_m":observation["front_x_m"],"relative_mass_drift":drift,"simulation_ok":simulation_ok,"history":history,"metadata":metadata,"project":str(project_path)}
    coarse,medium,fine=(runs[k] for k in ("coarse","medium","fine"))
    coarse_error=abs(coarse["front_at_0p2_s_m"]-fine["front_at_0p2_s_m"]); medium_error=abs(medium["front_at_0p2_s_m"]-fine["front_at_0p2_s_m"])
    checks={"all_solvers_advanced":all(x["simulation_ok"] for x in runs.values()),"element_count_increases":coarse["element_count"]<medium["element_count"]<fine["element_count"],"mass_conservation_lt_1pct":all(x["relative_mass_drift"]<0.01 for x in runs.values()),"fronts_finite":finite([x["front_at_0p2_s_m"] for x in runs.values()]),"medium_closer_to_fine":medium_error<=coarse_error+0.005}
    result.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"adaptive_sizing_status":"BLOCKED BY CURRENT PRODUCT MODE","adaptive_sizing_beta_note":"Documented FreeFlow beta feature, but no standalone FreeFlow application and no adaptive sizing object/module appeared in Rocky before or after a real beta-feature restart.","runs":runs,"coarse_to_fine_front_error_m":coarse_error,"medium_to_fine_front_error_m":medium_error})
except Exception:
    result["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    try: app.Exit()
    except Exception: pass
