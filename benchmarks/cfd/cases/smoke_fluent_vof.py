"""Case P: 2-D air-water VOF dam-break transient benchmark."""
from __future__ import annotations
import math
import numpy as np
from fluent_field_export import ALIASES,export_npz_from_ascii,stack_time_series_npz
from fluent_mesh import rectangular_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json
CASE="fluent_vof";L=3.;H=1.;W0=.6;HW=.8;DT=.005;STEPS=200
def main()->int:
    clean_case(CASE);mesh=OUT/f"{CASE}.msh";xs=[L*i/150 for i in range(151)];ys=[H*j/50 for j in range(51)];stats=rectangular_2d(mesh,xs,ys,left=("left-wall","wall"),right=("right-wall","wall"),bottom=("bottom-wall","wall"),top=("top-wall","wall"));payload=base_payload(CASE,"Case P: 2-D air-water VOF dam-break")
    hist=[];snaps=[]
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.general.solver.time="unsteady-1st-order";s.settings.setup.models.viscous.model="laminar"
            s.settings.setup.materials.fluid["water"]={"density":{"value":998.2},"viscosity":{"value":.001003}}
            mp=s.settings.setup.models.multiphase;mp.model="vof"
            phase_names=list(mp.phases.get_object_names());mp.phases[phase_names[0]].material="air";mp.phases[phase_names[1]].material="water"
            grav=s.settings.setup.general.operating_conditions.gravity;grav.enable=True;grav.components=[0.,-9.81,0.]
            s.settings.solution.run_calculation.parameters.time_step_size=DT;s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.cell_registers.create(name="water-column")
            reg=s.settings.solution.cell_registers["water_column"];reg.type.option="hexahedron";reg.type.hexahedron.min_point=[0.,0.,-1.];reg.type.hexahedron.max_point=[W0,HW,1.];reg.type.hexahedron.inside=True
            s.settings.solution.initialization.patch.calculate_patch(domain=phase_names[1],registers=["water_column"],variable="mp",use_custom_field_function=False,value=1.)
            allowed=list(s.fields.field_data.scalar_fields.allowed_values());vf=next((x for x in allowed if ("vof" in x.lower() or "volume-fraction" in x.lower()) and phase_names[1].lower() in x.lower()),None) or next((x for x in allowed if "vof" in x.lower()),None)
            if not vf:raise RuntimeError(f"No VOF field in {allowed}")
            ALIASES["volume_fraction"]=vf;qs=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity","velocity-magnitude",vf]
            surfaces=["interior","left-wall","right-wall","bottom-wall","top-wall"]
            for step in range(10,STEPS+1,10):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=10,max_iter_per_step=12);raw=OUT/f"{CASE}_sample_{step:04d}.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=surfaces,delimiter="comma",quantities=qs,location="node");rows=read_fluent_ascii_export(raw);a=np.asarray([r[vf] for r in rows]);wet=[r for r in rows if r[vf]>.5 and r["y-coordinate"]<.2];front=max((r["x-coordinate"] for r in wet),default=0.);hist.append({"time_s":step*DT,"front_x_m":front,"alpha_min":float(a.min()),"alpha_max":float(a.max()),"mean_alpha":float(a.mean())})
                if step in (40,80,120,160,200):
                    fp=OUT/f"{CASE}_snapshot_t{step*DT:.2f}.npz";meta={"case":"P","time_s":step*DT,"dt_s":DT,"phases":["air","water"],"field_source":vf,"units":{"coordinates":"m","velocity":"m/s","pressure":"Pa","volume_fraction":"1"},"fluent_version":"261"};chk=export_npz_from_ascii(raw,fp,fields=["velocity_x","velocity_y","pressure","volume_fraction"],metadata=meta,time=step*DT);snaps.append(fp)
                raw.unlink(missing_ok=True)
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        dset=OUT/f"{CASE}_timespace_dataset.npz";dchk=stack_time_series_npz(snaps,dset,fields=["velocity_x","velocity_y","pressure","volume_fraction"],metadata={"case":"P","representation":"field[time,node]","phases":["air","water"],"fluent_version":"261"})
        initial=W0*HW/(L*H);drift=abs(hist[-1]["mean_alpha"]-hist[0]["mean_alpha"])/max(hist[0]["mean_alpha"],1e-30);csvp=write_csv(OUT/f"{CASE}_front.csv",list(hist[0]),hist);fsvg=svg_xy_plot(OUT/f"{CASE}_front.svg",[(x["time_s"],x["front_x_m"]) for x in hist],title="Case P: dam-break front propagation",xlabel="time (s)",ylabel="front x (m)");withlast=np.load(snaps[-1]);vsvg=svg_field_map(OUT/f"{CASE}_volume_fraction.svg",[(x,y,a) for (x,y),a in zip(withlast["coordinates"],withlast["volume_fraction"])],title="Case P: water volume fraction at t=1 s");withlast.close()
        checks={"vof_field_bounded":min(x["alpha_min"] for x in hist)>-1e-6 and max(x["alpha_max"] for x in hist)<1+1e-6,"initial_water_fraction_reasonable":abs(hist[0]["mean_alpha"]-initial)<.04,"front_advances":hist[-1]["front_x_m"]>W0*1.5,"volume_fraction_drift_lt_8pct":drift<.08,"timespace_dataset_valid":dchk["valid"],"five_snapshots":len(snaps)==5,"finite_history":all(all(math.isfinite(v) for v in x.values()) for x in hist)}
        payload.update({"model":{"method":"VOF","phases":["air","water"],"gravity_m_s2":[0,-9.81],"initial_water_column_m":[W0,HW]},"mesh":{**stats,"nx":150,"ny":50},"time":{"dt_s":DT,"steps":STEPS,"final_time_s":1.},"results":{"final_front_x_m":hist[-1]["front_x_m"],"initial_sample_mean_alpha":hist[0]["mean_alpha"],"final_mean_alpha":hist[-1]["mean_alpha"],"relative_alpha_drift":drift},"dataset":dchk,"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [mesh,csvp,fsvg,vsvg,dset,OUT/f"{CASE}.cas.h5",*snaps]]})
    except Exception as exc:payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
