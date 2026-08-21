"""Case D: automated 3-D numerical wind tunnel around a simple block."""
from __future__ import annotations
import math
import numpy as np
from fluent_mesh import block_wind_tunnel_3d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,write_csv,write_json

CASE="fluent_wind_tunnel"; U=10.0; RHO=1.225; MU=1.7894e-5
BLOCK=(0.0,1.5,-0.5,0.5,0.0,1.0)
def seg(a,b,n): return [a+(b-a)*i/n for i in range(n+1)]
def merge(*parts): return sorted(set(round(v,12) for p in parts for v in p))

def main()->int:
    clean_case(CASE); mesh=OUT/f"{CASE}.msh"
    xs=merge(seg(-3,0,12),seg(0,1.5,8),seg(1.5,8,24)); ys=merge(seg(-2,-.5,6),seg(-.5,.5,8),seg(.5,2,6)); zs=merge(seg(0,1,10),seg(1,3,12))
    stats=block_wind_tunnel_3d(mesh,xs=xs,ys=ys,zs=zs,block=BLOCK)
    payload=base_payload(CASE,"3-D steady numerical wind tunnel")
    payload["model"]={"fluid":"air","velocity_m_s":U,"block_m":{"length":1.5,"width":1.0,"height":1.0},"turbulence_model":"k-omega SST","reference_area_m2":1.0}
    payload["mesh"]={**stats,"type":"body-fitted Cartesian hexahedral","nx":len(xs)-1,"ny":len(ys)-1,"nz":len(zs)-1}
    try:
        with fluent_session(dimension=3,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.viscous.model="k-omega"
            if hasattr(s.settings.setup.models.viscous,"k_omega_model"): s.settings.setup.models.viscous.k_omega_model="sst"
            air=s.settings.setup.materials.fluid["air"]; air.density.value=RHO; air.viscosity.value=MU
            vin=s.settings.setup.boundary_conditions.velocity_inlet["inlet"]; vin.momentum.velocity_magnitude.value=U; vin.turbulence.turbulent_intensity=.05; vin.turbulence.turbulent_viscosity_ratio=10
            s.settings.results.surfaces.plane_slice["center-plane"]={"normal":[0.0,1.0,0.0],"distance_from_origin":0.0}
            s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=700)
            allowed=list(s.fields.field_data.scalar_fields.allowed_values()); sx=next((f for f in ("x-wall-shear","wall-shear-x") if f in allowed),None)
            quantities=["x-coordinate","y-coordinate","z-coordinate","pressure","x-velocity","velocity-magnitude"]+([sx] if sx else [])
            raw=OUT/f"{CASE}_raw.csv"; s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5")); s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["model-wall","center-plane"],delimiter="comma",quantities=quantities,location="node")
        rows=read_fluent_ascii_export(raw); x0,x1,y0,y1,z0,z1=BLOCK
        model=[r for r in rows if x0-1e-8<=r["x-coordinate"]<=x1+1e-8 and y0-1e-8<=r["y-coordinate"]<=y1+1e-8 and z0-1e-8<=r["z-coordinate"]<=z1+1e-8 and (abs(r["x-coordinate"]-x0)<1e-8 or abs(r["x-coordinate"]-x1)<1e-8 or abs(r["y-coordinate"]-y0)<1e-8 or abs(r["y-coordinate"]-y1)<1e-8 or abs(r["z-coordinate"]-z1)<1e-8)]
        front=[r for r in model if abs(r["x-coordinate"]-x0)<1e-8]; rear=[r for r in model if abs(r["x-coordinate"]-x1)<1e-8]
        pfront=float(np.mean([r["pressure"] for r in front])); prear=float(np.mean([r["pressure"] for r in rear])); drag_pressure=(pfront-prear)*1.0
        drag_shear=0.0
        if sx:
            top=[r for r in model if abs(r["z-coordinate"]-z1)<1e-8]; sides=[r for r in model if abs(abs(r["y-coordinate"])-.5)<1e-8]
            drag_shear=float(np.mean([r[sx] for r in top]))*1.5+float(np.mean([r[sx] for r in sides]))*3.0
        drag=drag_pressure+drag_shear; cd=drag/(.5*RHO*U**2)
        center=[r for r in rows if abs(r["y-coordinate"])<1e-8 and not (x0<=r["x-coordinate"]<=x1 and z0<=r["z-coordinate"]<=z1)]
        wake=[r for r in center if x1<r["x-coordinate"]<x1+3 and .2<r["z-coordinate"]<.8]
        cp_rows=[{"x_m":r["x-coordinate"],"y_m":r["y-coordinate"],"z_m":r["z-coordinate"],"pressure_pa":r["pressure"],"cp":r["pressure"]/(.5*RHO*U**2)} for r in model]
        csv=write_csv(OUT/f"{CASE}_field_data.csv",list(cp_rows[0]),cp_rows)
        psvg=svg_field_map(OUT/f"{CASE}_pressure_distribution.svg",[(r["x_m"],r["z_m"],r["cp"]) for r in cp_rows],title="Case D: block surface pressure coefficient",ylabel="z (m)")
        vsvg=svg_field_map(OUT/f"{CASE}_velocity_distribution.svg",[(r["x-coordinate"],r["z-coordinate"],r["velocity-magnitude"]) for r in center],title="Case D: center-plane velocity magnitude",ylabel="z (m)")
        checks={"positive_drag":drag>0,"bluff_body_cd_range":0.4<cd<3.0,"wake_deficit_visible":min((r["velocity-magnitude"] for r in wake),default=U)<.8*U,"turbulent_reynolds":RHO*U/MU>1e5}
        payload.update({"results":{"drag_n":drag,"pressure_drag_n":drag_pressure,"viscous_drag_estimate_n":drag_shear,"drag_coefficient":cd,"lift":"not applicable: floor-mounted block","front_mean_pressure_pa":pfront,"rear_mean_pressure_pa":prear,"minimum_near_wake_velocity_m_s":min(r["velocity-magnitude"] for r in wake)},"checks":checks,"convergence":{"iterations_requested":700},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(p.resolve()) for p in (mesh,raw,csv,psvg,vsvg,OUT/f"{CASE}.cas.h5")]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
