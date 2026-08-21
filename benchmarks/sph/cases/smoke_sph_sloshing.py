"""Case C: off-resonance and near-resonance native SPH tank sloshing."""

from pathlib import Path
import json
import math
import traceback

from free_surface_sph_common import *
from sph_field_export import export_lagrangian, read_sph_steps


OUT=OUTPUT_ROOT/"case_c_sloshing"; OUT.mkdir(parents=True,exist_ok=True); RESULT=OUT/"result.json"
result={"case":"C","status":"FAIL","stage":"initializing"}
try:
    # The initial column settles to approximately 36 mm over the full tank
    # footprint.  Delay the excitation so the frequency comparison is not
    # dominated by the initial gravitational collapse.
    length=0.08; depth=0.036; wave_number=math.pi/length
    omega_1=math.sqrt(GRAVITY*wave_number*math.tanh(wave_number*depth)); frequency_1=omega_1/(2*math.pi)
    frequencies={"off_resonance":0.50*frequency_1,"near_resonance":frequency_1}
    runs={}
    for label,frequency in frequencies.items():
        project=app.CreateProject(); study=project.GetStudy(); study.SetName(f"Case C - {label}")
        run_dir=OUT/label; run_dir.mkdir(parents=True,exist_ok=True)
        project_path=run_dir/f"{label}.rocky"; project.SaveProject(str(project_path))
        sph,water,physics=configure_water_sph(study,size_m=0.0075,solver_model="IISPH")
        tank,boundary_values=import_open_tank(study,asset="sph_hydro_tank.stl")
        add_sph_volume(study,name="Sloshing Water",center_m=(0.0,0.0,0.035),dimensions_m=(0.06,0.04,0.06),sph_size_m=0.0075)
        frame=study.GetMotionFrameSource().NewFrame(); frame.SetName(f"Sinusoidal {frequency:.6g} Hz")
        frame.AddVibrationMotion(start_time=(0.50,"s"),stop_time=(2.0,"s"),initial_frequency=(frequency,"Hz"),initial_amplitude=(0.002,"m"),direction=((1.0,0.0,0.0),"m"))
        frame.ApplyTo(tank); set_domain(study,(-0.10,-0.08,-0.03),(0.10,0.08,0.18))
        simulation_ok=solve(study,project,project_path,duration_s=2.0,output_dt_s=0.025)
        metadata=export_lagrangian(study,run_dir/"sph_lagrangian.csv"); steps,_=read_sph_steps(study)
        history=[]
        for t,rows in steps:
            left=sorted((float(r["position_z_m"])+0.00375 for r in rows if float(r["position_x_m"])<-0.015),reverse=True)
            right=sorted((float(r["position_z_m"])+0.00375 for r in rows if float(r["position_x_m"])>0.015),reverse=True)
            center_x=sum(float(r["mass_kg"])*float(r["position_x_m"]) for r in rows)/max(sum(float(r["mass_kg"]) for r in rows),1e-30)
            # Average the three highest end-region elements.  This is a less
            # noisy free-surface estimator than a single maximum element.
            left_eta=sum(left[:3])/len(left[:3]) if left else math.nan
            right_eta=sum(right[:3])/len(right[:3]) if right else math.nan
            history.append({"time_s":t,"left_surface_m":left_eta,"right_surface_m":right_eta,"surface_difference_m":left_eta-right_eta,"fluid_center_x_m":center_x})
        active=[x["surface_difference_m"] for x in history if x["time_s"]>=0.75 and math.isfinite(x["surface_difference_m"])]
        amplitude=0.5*(max(active)-min(active)) if active else math.nan
        runs[label]={"frequency_hz":frequency,"simulation_ok":simulation_ok,"surface_response_amplitude_m":amplitude,"history":history,"metadata":metadata,"project":str(project_path)}
    off=runs["off_resonance"]["surface_response_amplitude_m"]; near=runs["near_resonance"]["surface_response_amplitude_m"]
    checks={"both_solvers_advanced":all(x["simulation_ok"] for x in runs.values()),"finite_amplitudes":finite([off,near]),"near_resonance_response_larger":near>1.05*off,"time_histories":all(len(x["history"])>=20 for x in runs.values())}
    result.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"tank_length_m":length,"fill_depth_m":depth,"settling_time_s":0.5,"theoretical_first_frequency_hz":frequency_1,"excitation_amplitude_m":0.002,"runs":runs,"response_ratio_near_to_off":near/max(off,1e-30)})
except Exception:
    result["error"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    try: app.Exit()
    except Exception: pass
