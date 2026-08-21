"""Case B: narrow-3D native SPH dam-break benchmark."""

from pathlib import Path
import json
import math
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, project_xz_to_npz, read_sph_steps


OUT = OUTPUT_ROOT / "case_b_dam_break"
OUT.mkdir(parents=True, exist_ok=True)
RESULT = OUT / "result.json"
result = {"case":"B", "status":"FAIL", "stage":"initializing"}
try:
    project = app.CreateProject(); study = project.GetStudy(); study.SetName("Case B - SPH Dam Break")
    project_path=OUT/"case_b_dam_break.rocky"; project.SaveProject(str(project_path))
    sph, water, physics = configure_water_sph(study, size_m=0.01, solver_model="IISPH")
    tank, boundary_values = import_open_tank(study)
    # Exact 1:10 geometric scale of the validated Fluent VOF case:
    # tank 3 x 1 m -> 0.3 x 0.1 m; column 0.6 x 0.8 m -> 0.06 x 0.08 m.
    initial_center_x=-0.115; initial_width=0.06; initial_height=0.08
    add_sph_volume(
        study, name="Dam Water Column", center_m=(initial_center_x,0.0,0.045),
        dimensions_m=(initial_width,0.04,initial_height), sph_size_m=0.01,
    )
    set_domain(study)
    result["stage"]="simulation"
    simulation_ok=solve(study,project,project_path,duration_s=0.60,output_dt_s=0.05)
    result["stage"]="validation"
    metadata=export_lagrangian(study,OUT/"sph_lagrangian.csv")
    projection=project_xz_to_npz(study,OUT/"eulerian_projection.npz",xlim=(-0.15,0.15),zlim=(0.0,0.15),shape=(61,31),smoothing_length_m=0.012)
    steps,_=read_sph_steps(study)
    history=[]; masses=[]
    for time_value,rows in steps:
        front=max((float(r["position_x_m"])+0.005 for r in rows),default=math.nan)
        surface=max((float(r["position_z_m"])+0.005 for r in rows),default=math.nan)
        mass=sum(float(r["mass_kg"]) for r in rows)
        speeds=[math.hypot(float(r["velocity_x_m_per_s"]),float(r["velocity_z_m_per_s"])) for r in rows]
        history.append({"time_s":time_value,"front_x_m":front,"free_surface_height_m":surface,"max_speed_m_per_s":max(speeds,default=0.0),"mass_kg":mass})
        masses.append(mass)
    mass_drift=(max(masses)-min(masses))/max(masses[0],1e-30) if masses else math.inf
    initial_front=initial_center_x+0.5*initial_width
    finite_history=all(finite(item.values()) for item in history)
    checks={
        "solver_advanced":simulation_ok,
        "at_least_100_elements":metadata["element_counts"][-1]>=100 if metadata["element_counts"] else False,
        "front_advances":history[-1]["front_x_m"]>initial_front+0.04 if history else False,
        "mass_conservation_lt_1pct":mass_drift<0.01,
        "finite_history":finite_history,
        "five_or_more_snapshots":len(history)>=5,
        "projection_finite":all(math.isfinite(x) for x in projection["coverage_fraction"]),
    }
    result.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,
        "element_size_m":0.01,"element_count":metadata["element_counts"][-1] if metadata["element_counts"] else 0,
        "relative_mass_drift":mass_drift,"history":history,"metadata":metadata,"projection":projection,
        "project":str(project_path),"boundary_type_values":boundary_values})
except Exception:
    result["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    try: app.Exit()
    except Exception: pass
