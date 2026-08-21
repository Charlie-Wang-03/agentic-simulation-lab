"""Case N: low-cost 3-D transient WALE LES cylinder automation smoke test."""
from __future__ import annotations
import math
import numpy as np
from fluent_field_export import ALIASES,export_npz_from_ascii,stack_time_series_npz
from fluent_mesh import cylinder_ogrid_3d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_les_des"; D=1.; R=.5; SPAN=2.; U=1.; RHO=1.; RE=1000.; MU=.001; DT=.025; STEPS=640
PROBES={"p1":(1.,0.,1.),"p2":(2.,.5,1.),"p3":(4.,0.,1.)}
def pick(a,*n):return next((x for x in n if x in a),None)
def coeff(rows,sx,sy):
    rings={}
    for r in rows:
        if abs(math.hypot(r["x-coordinate"],r["y-coordinate"])-R)<1e-5:rings.setdefault(round(r["z-coordinate"],8),[]).append(r)
    cs=[]
    for ring in rings.values():
        u={(round(r["x-coordinate"],8),round(r["y-coordinate"],8)):r for r in ring}; rr=sorted(u.values(),key=lambda r:math.atan2(r["y-coordinate"],r["x-coordinate"]))
        th=np.unwrap(np.asarray([math.atan2(r["y-coordinate"],r["x-coordinate"]) for r in rr])); th=np.r_[th,th[0]+2*math.pi]; p=np.asarray([r["pressure"] for r in rr]); pp=np.r_[p,p[0]]
        fx=float(np.trapezoid(-pp*np.cos(th)*R,th)); fy=float(np.trapezoid(-pp*np.sin(th)*R,th))
        if sx:
            v=np.asarray([r.get(sx,0) for r in rr]);fx+=float(np.trapezoid(np.r_[v,v[0]]*R,th))
        if sy:
            v=np.asarray([r.get(sy,0) for r in rr]);fy+=float(np.trapezoid(np.r_[v,v[0]]*R,th))
        cs.append((fx/(.5*RHO*U*U*D),fy/(.5*RHO*U*U*D)))
    return tuple(np.mean(cs,axis=0))

def main()->int:
    clean_case(CASE);mesh=OUT/f"{CASE}.msh";stats=cylinder_ogrid_3d(mesh,radius=R,half_length=10.,half_height=8.,span=SPAN,nr=32,nt=96,nz=8)
    payload=base_payload(CASE,"Case N: 3-D transient WALE LES cylinder")
    hist=[];snaps=[]
    try:
        with fluent_session(dimension=3,processor_count=2,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh));s.settings.setup.general.solver.time="unsteady-2nd-order";s.settings.setup.models.viscous.model="large-eddy-simulation";s.settings.setup.models.viscous.subgrid_scale_model="les-subgrid-wale"
            air=s.settings.setup.materials.fluid["air"];air.density.value=RHO;air.viscosity.value=MU
            vin=s.settings.setup.boundary_conditions.velocity_inlet["inlet"];vin.momentum.velocity_magnitude.value=U
            for n,p in PROBES.items():s.settings.results.surfaces.point_surface[n]={"point":list(p)}
            s.settings.results.surfaces.plane_slice["midspan"]={"normal":[0.,0.,1.],"distance_from_origin":SPAN/2}
            s.settings.solution.run_calculation.parameters.time_step_size=DT;s.settings.solution.initialization.hybrid_initialize();s.settings.solution.initialization.patch.calculate_patch(cell_zones=["fluid"],variable="y-velocity",value=.08)
            allowed=list(s.fields.field_data.scalar_fields.allowed_values());sx=pick(allowed,"x-wall-shear","wall-shear-x");sy=pick(allowed,"y-wall-shear","wall-shear-y");vort=pick(allowed,"vorticity-magnitude","vorticity-mag","vorticity")
            if not vort:raise RuntimeError("No Fluent vorticity scalar available")
            ALIASES["vorticity"]=vort;qs=["x-coordinate","y-coordinate","z-coordinate","pressure","x-velocity","y-velocity","z-velocity",vort]+[x for x in (sx,sy) if x]
            for step in range(4,STEPS+1,4):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=4,max_iter_per_step=10)
                raw=OUT/f"{CASE}_sample_{step:04d}.csv";s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["cylinder",*PROBES],delimiter="comma",quantities=qs,location="node")
                rows=read_fluent_ascii_export(raw);cd,cl=coeff(rows,sx,sy);item={"time_s":step*DT,"cd":cd,"cl":cl}
                pts=[r for r in rows if math.hypot(r["x-coordinate"],r["y-coordinate"])>R*1.01]
                for n,p in PROBES.items():
                    r=min(pts,key=lambda x:sum((x[k]-p[i])**2 for i,k in enumerate(("x-coordinate","y-coordinate","z-coordinate"))));item.update({f"{n}_u":r["x-velocity"],f"{n}_v":r["y-velocity"],f"{n}_p":r["pressure"]})
                hist.append(item);raw.unlink(missing_ok=True)
                if step in (320,400,480,560,640):
                    fr=OUT/f"{CASE}_snapshot_t{step*DT:.1f}_raw.csv";fp=OUT/f"{CASE}_snapshot_t{step*DT:.1f}.npz";s.settings.file.export.ascii(file_name=str(fr),surface_name_list=["midspan"],delimiter="comma",quantities=qs,location="node")
                    meta={"case":"N","Re":RE,"time_s":step*DT,"dt_s":DT,"method":"3-D WALE LES; exported midspan plane","units":{"coordinates":"m","velocity":"m/s","pressure":"Pa","vorticity":"1/s"},"fluent_version":"261"}
                    chk=export_npz_from_ascii(fr,fp,fields=["velocity_x","velocity_y","velocity_z","pressure","vorticity"],metadata=meta,time=step*DT)
                    if not chk["valid"]:raise RuntimeError(f"invalid snapshot {fp}")
                    snaps.append(fp)
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        stat=[r for r in hist if r["time_s"]>=8.];t=np.asarray([r["time_s"] for r in stat]);cl=np.asarray([r["cl"] for r in stat]);cd=np.asarray([r["cd"] for r in stat]);f=np.fft.rfftfreq(len(cl),d=.1);a=np.abs(np.fft.rfft(cl-np.mean(cl)));a[0]=0;freq=float(f[np.argmax(a)]);st=freq*D/U
        dataset=OUT/f"{CASE}_timespace_dataset.npz";dchk=stack_time_series_npz(snaps,dataset,fields=["velocity_x","velocity_y","velocity_z","pressure","vorticity"],metadata={"case":"N","Re":RE,"representation":"midspan field[time,node]","fluent_version":"261"})
        csvp=write_csv(OUT/f"{CASE}_history.csv",list(hist[0]),hist);clsvg=svg_xy_plot(OUT/f"{CASE}_cl.svg",[(r["time_s"],r["cl"]) for r in hist],title="Case N: 3-D LES lift history",xlabel="tU/D",ylabel="Cl")
        with np.load(snaps[-1]) as d:vsvg=svg_field_map(OUT/f"{CASE}_vorticity.svg",[(x,y,v) for (x,y,_),v in zip(d["coordinates"],d["vorticity"])],title="Case N: midspan vorticity at t=16")
        min_spacing=.02;cfl=U*DT/min_spacing;checks={"les_model_ran":True,"nonzero_unsteady_lift":float(np.std(cl))>.01,"dominant_frequency_reasonable":.1<st<.35,"timespace_dataset_valid":dchk["valid"],"five_snapshots":len(snaps)==5,"finite_history":all(all(math.isfinite(v) for v in r.values()) for r in hist)}
        payload.update({"model":{"Re":RE,"method":"3-D WALE LES","span_D":SPAN},"mesh":{**stats,"type":"extruded O-grid hexahedral"},"time":{"dt_s":DT,"steps":STEPS,"final_time_s":STEPS*DT,"sample_interval_s":.1,"statistics_window_s":[8.,16.],"estimated_max_cfl":cfl},"results":{"mean_cd":float(np.mean(cd)),"cl_rms":float(np.std(cl)),"dominant_frequency_hz":freq,"strouhal":st,"samples":len(hist)},"dataset":dchk,"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [mesh,csvp,clsvg,vsvg,dataset,OUT/f"{CASE}.cas.h5",*snaps]]})
    except Exception as exc:payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload);print(payload);return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
