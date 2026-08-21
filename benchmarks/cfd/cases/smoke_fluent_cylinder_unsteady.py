"""Case H: unsteady Re=100 circular-cylinder vortex shedding."""

from __future__ import annotations

import math
from pathlib import Path
import csv
import numpy as np

from fluent_field_export import export_npz_from_ascii
from fluent_mesh import cylinder_ogrid_2d
from fluent_smoke_common import OUT, base_payload, clean_case, fluent_session, read_fluent_ascii_export, svg_field_map, svg_xy_plot, write_csv, write_json

CASE="fluent_cylinder_unsteady"; D=1.; R=.5; U=1.; RHO=1.; MU=.01; DT=.05
PROBES={"p1":(1.0,0.0),"p2":(2.0,0.5),"p3":(4.0,0.0)}


def cylinder_coeff(rows, shear_x, shear_y):
    surf={}
    for r in rows:
        if abs(math.hypot(r["x-coordinate"],r["y-coordinate"])-R)<1e-5:
            surf[(round(r["x-coordinate"],8),round(r["y-coordinate"],8))]=r
    rs=sorted(surf.values(),key=lambda r:math.atan2(r["y-coordinate"],r["x-coordinate"]))
    th=np.unwrap(np.asarray([math.atan2(r["y-coordinate"],r["x-coordinate"]) for r in rs])); th=np.r_[th,th[0]+2*math.pi]
    p=np.asarray([r["pressure"] for r in rs]); pp=np.r_[p,p[0]]
    fx=float(np.trapezoid(-pp*np.cos(th)*R,th)); fy=float(np.trapezoid(-pp*np.sin(th)*R,th))
    if shear_x:
        sx=np.asarray([r.get(shear_x,0.) for r in rs]); fx += float(np.trapezoid(np.r_[sx,sx[0]]*R,th))
    if shear_y:
        sy=np.asarray([r.get(shear_y,0.) for r in rs]); fy += float(np.trapezoid(np.r_[sy,sy[0]]*R,th))
    q=.5*RHO*U*U
    return fx/(q*D),fy/(q*D)


def main()->int:
    mesh=OUT/f"{CASE}.msh"; saved=OUT/f"{CASE}.cas.h5"
    # A normal invocation is deterministic and starts from zero.  The prior
    # continuation path was used only while diagnosing transient saturation.
    continuing=False; clean_case(CASE)
    stats=cylinder_ogrid_2d(mesh,radius=R,half_length=15.,half_height=10.,nr=44,nt=128)
    payload=base_payload(CASE,"Case H: 2-D transient laminar vortex shedding at Re=100")
    payload["mesh"]={**stats,"type":"mapped O-grid quadrilateral","radial":44,"circumferential":128}
    history=[]; snapshot_files=[]
    if continuing:
        with (OUT/f"{CASE}_history.csv").open(encoding="utf-8-sig") as f:
            history=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            if continuing:
                s.settings.file.read_case_data(file_name=str(saved))
            else:
                s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.general.solver.time="unsteady-2nd-order"
                s.settings.setup.models.viscous.model="laminar"
                air=s.settings.setup.materials.fluid["air"]; air.density.value=RHO; air.viscosity.value=MU
                inlet=s.settings.setup.boundary_conditions.velocity_inlet["inlet"]
                inlet.momentum.velocity_spec="Components"; inlet.momentum.velocity_components[0].value=U; inlet.momentum.velocity_components[1].value=0.0
                for name,(x,y) in PROBES.items(): s.settings.results.surfaces.point_surface[name]={"point":[x,y,0.]}
                s.settings.solution.run_calculation.parameters.time_step_size=DT
                s.settings.solution.initialization.hybrid_initialize()
                # Break exact numerical symmetry to seed the physical Hopf mode.
                s.settings.solution.initialization.patch.calculate_patch(cell_zones=["fluid"], variable="y-velocity", value=0.08)
            allowed=list(s.fields.field_data.scalar_fields.allowed_values())
            sx=next((f for f in ("x-wall-shear","wall-shear-x") if f in allowed),None)
            sy=next((f for f in ("y-wall-shear","wall-shear-y") if f in allowed),None)
            quantities=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity"]+[x for x in (sx,sy) if x]
            total_steps=2400; sample_every=5; start_step=0
            snapshot_targets=(1800,1950,2100,2250,2400)
            for step in range(start_step+sample_every,total_steps+1,sample_every):
                s.settings.solution.run_calculation.dual_time_iterate(time_step_count=sample_every,max_iter_per_step=12)
                raw=OUT/f"{CASE}_sample_{step:04d}.csv"
                s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["cylinder",*PROBES],delimiter="comma",quantities=quantities,location="node")
                rows=read_fluent_ascii_export(raw); cd,cl=cylinder_coeff(rows,sx,sy)
                item={"time_s":step*DT,"cd":cd,"cl":cl}
                point_rows=[r for r in rows if math.hypot(r["x-coordinate"],r["y-coordinate"])>R*1.01]
                for name,(x,y) in PROBES.items():
                    pr=min(point_rows,key=lambda r:(r["x-coordinate"]-x)**2+(r["y-coordinate"]-y)**2)
                    item.update({f"{name}_u":pr["x-velocity"],f"{name}_v":pr["y-velocity"],f"{name}_p":pr["pressure"]})
                history.append(item); raw.unlink(missing_ok=True)
                if step in snapshot_targets:
                    fraw=OUT/f"{CASE}_snapshot_t{step*DT:.1f}_raw.csv"; fnpz=OUT/f"{CASE}_snapshot_t{step*DT:.1f}.npz"
                    s.settings.file.export.ascii(file_name=str(fraw),surface_name_list=["interior"],delimiter="comma",quantities=["x-coordinate","y-coordinate","x-velocity","y-velocity","pressure","velocity-magnitude"],location="node")
                    meta={"case":"H","Re":100,"time_s":step*DT,"dt_s":DT,"units":{"coordinates":"m","velocity_x":"m/s","velocity_y":"m/s","pressure":"Pa"},"fluent_version":"261","solver":"transient second-order implicit laminar"}
                    check=export_npz_from_ascii(fraw,fnpz,fields=["velocity_x","velocity_y","pressure"],metadata=meta,time=step*DT)
                    if not check["valid"]: raise RuntimeError(f"invalid snapshot {fnpz}")
                    snapshot_files += [fraw,fnpz]
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        stat=[r for r in history if r["time_s"]>=80.]
        times=np.asarray([r["time_s"] for r in stat]); cls=np.asarray([r["cl"] for r in stat]); cds=np.asarray([r["cd"] for r in stat])
        centered=cls-np.mean(cls); freq=np.fft.rfftfreq(len(centered),d=sample_every*DT); amp=np.abs(np.fft.rfft(centered)); amp[0]=0
        shedding=float(freq[int(np.argmax(amp))]); st=shedding*D/U
        cl_rms=float(np.sqrt(np.mean(centered**2))); mean_cd=float(np.mean(cds))
        half=len(centered)//2; rms1=float(np.sqrt(np.mean(centered[:half]**2))); rms2=float(np.sqrt(np.mean(centered[half:]**2)))
        csvp=write_csv(OUT/f"{CASE}_history.csv",list(history[0]),history)
        clsvg=svg_xy_plot(OUT/f"{CASE}_cl_history.svg",[(r["time_s"],r["cl"]) for r in history],title="Case H: lift coefficient history",xlabel="tU/D",ylabel="Cl")
        last=read_fluent_ascii_export(snapshot_files[-2]); vsvg=svg_field_map(OUT/f"{CASE}_wake_velocity.svg",[(r["x-coordinate"],r["y-coordinate"],math.hypot(r["x-velocity"],r["y-velocity"])) for r in last],title="Case H: periodic wake velocity at t=40")
        checks={"strouhal_in_classic_range":.14<st<.19,"mean_cd_in_classic_range":1.0<mean_cd<1.7,"periodic_lift_nonzero":cl_rms>.05,"late_rms_stationary":abs(rms2-rms1)/max(rms2,1e-12)<.35,"all_snapshots_valid":True,"finite_history":all(all(math.isfinite(v) for v in r.values()) for r in history)}
        final_t=120.; stat0=80.
        payload.update({"model":{"Re":100,"rho_kg_m3":RHO,"mu_pa_s":MU,"U_m_s":U,"D_m":D,"transient":"second-order implicit","initial_y_velocity_disturbance_m_s":.08},"time":{"dt_s":DT,"steps":total_steps,"final_time_s":final_t,"sample_interval_s":.25,"statistics_window_s":[stat0,final_t]},"results":{"mean_cd":mean_cd,"cl_rms":cl_rms,"cl_peak_to_peak":float(np.ptp(cls)),"shedding_frequency_hz":shedding,"strouhal_number":st,"late_window_rms_ratio":rms2/max(rms1,1e-12),"history_samples":len(history),"snapshots":5},"benchmark":{"classic_Re100":"St about 0.16-0.17; mean Cd about 1.3-1.4"},"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(p.resolve()) for p in [mesh,csvp,clsvg,vsvg,OUT/f"{CASE}.cas.h5",*snapshot_files]]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
