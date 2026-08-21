"""Case O: two-zone transient sliding mesh with a four-lobed impeller."""
from __future__ import annotations
import math
import numpy as np
from fluent_mesh import rotor_stator_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_sliding_mesh";RHO=1.;MU=.01;OMEGA=20.;RPM=OMEGA*60/(2*math.pi);DT=.002;STEPS=400
def torque(rows,sx,sy):
    u={(round(r["x-coordinate"],9),round(r["y-coordinate"],9)):r for r in rows};rr=sorted(u.values(),key=lambda r:math.atan2(r["y-coordinate"],r["x-coordinate"]));t=0.
    for i,a in enumerate(rr):
        b=rr[(i+1)%len(rr)];dx=b["x-coordinate"]-a["x-coordinate"];dy=b["y-coordinate"]-a["y-coordinate"];ds=math.hypot(dx,dy);p=.5*(a["pressure"]+b["pressure"]);fx=-p*dy;fy=p*dx
        if sx:fx+=.5*(a.get(sx,0)+b.get(sx,0))*ds
        if sy:fy+=.5*(a.get(sy,0)+b.get(sy,0))*ds
        x=.5*(a["x-coordinate"]+b["x-coordinate"]);y=.5*(a["y-coordinate"]+b["y-coordinate"]);t+=x*fy-y*fx
    return t
def main()->int:
    clean_case(CASE);mesh=OUT/f"{CASE}.msh";stats=rotor_stator_2d(mesh,inner_radius=.35,interface_radius=1.,outer_radius=3.,nr_rotor=16,nr_stator=20,nt=128);payload=base_payload(CASE,"Case O: transient rotating-zone sliding mesh")
    hist=[];snaps=[]
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.general.solver.time="unsteady-2nd-order";s.settings.setup.models.viscous.model="laminar"
            air=s.settings.setup.materials.fluid["air"];air.density.value=RHO;air.viscosity.value=MU
            s.settings.setup.mesh_interfaces.create_manually(name="sliding",zone_list_1=["rotor-interface"],zone_list_2=["stator-interface"],matching=False,ignore_area_difference=False)
            rotor=s.settings.setup.cell_zone_conditions.fluid["rotor"];rotor.mesh_motion.enable=True;rotor.mesh_motion.mgrid_omega.value=OMEGA
            s.settings.solution.run_calculation.parameters.time_step_size=DT;s.settings.solution.initialization.hybrid_initialize();allowed=list(s.fields.field_data.scalar_fields.allowed_values());sx=next((f for f in ("x-wall-shear","wall-shear-x") if f in allowed),None);sy=next((f for f in ("y-wall-shear","wall-shear-y") if f in allowed),None);qs=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity","velocity-magnitude"]+[x for x in (sx,sy) if x]
            for step in range(5,STEPS+1,5):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=5,max_iter_per_step=15);raw=OUT/f"{CASE}_sample_{step:04d}.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["impeller-wall"],delimiter="comma",quantities=qs,location="node");rows=read_fluent_ascii_export(raw);hist.append({"time_s":step*DT,"angle_rad":OMEGA*step*DT,"torque_Nm_per_m":torque(rows,sx,sy)});raw.unlink(missing_ok=True)
                if step in (250,300,350,400):
                    fr=OUT/f"{CASE}_snapshot_t{step*DT:.3f}.csv";s.settings.file.export.ascii(file_name=str(fr),surface_name_list=["interior"],delimiter="comma",quantities=qs,location="node");snaps.append(fr)
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        late=[x for x in hist if x["time_s"]>=.5];vals=np.asarray([x["torque_Nm_per_m"] for x in late]);mean=float(np.mean(vals));amp=float(np.ptp(vals));csvp=write_csv(OUT/f"{CASE}_torque.csv",list(hist[0]),hist);tsvg=svg_xy_plot(OUT/f"{CASE}_torque.svg",[(x["time_s"],x["torque_Nm_per_m"]) for x in hist],title="Case O: sliding-mesh impeller torque",xlabel="time (s)",ylabel="torque (N m/m)");last=read_fluent_ascii_export(snaps[-1]);vsvg=svg_field_map(OUT/f"{CASE}_velocity.svg",[(r["x-coordinate"],r["y-coordinate"],r["velocity-magnitude"]) for r in last],title="Case O: rotating flow velocity")
        checks={"two_fluid_zones":stats["fluid_zones"]==2,"sliding_interface_created":True,"nonzero_torque":abs(mean)>1e-4,"periodic_torque_variation":amp>1e-5,"finite_history":all(math.isfinite(x["torque_Nm_per_m"]) for x in hist),"four_snapshots":len(snaps)==4}
        payload.update({"model":{"method":"transient sliding mesh","rotating_zone":"rotor","stationary_zone":"stator","omega_rad_s":OMEGA,"rpm":RPM,"interface":"non-conformal rotor-interface/stator-interface"},"mesh":{**stats,"type":"two-zone quadrilateral annuli"},"time":{"dt_s":DT,"steps":STEPS,"final_time_s":STEPS*DT,"rotor_period_s":2*math.pi/OMEGA,"steps_per_revolution":2*math.pi/OMEGA/DT},"results":{"mean_late_torque_Nm_per_m":mean,"torque_peak_to_peak":amp,"samples":len(hist)},"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [mesh,csvp,tsvg,vsvg,OUT/f"{CASE}.cas.h5",*snaps]]})
    except Exception as exc:payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
