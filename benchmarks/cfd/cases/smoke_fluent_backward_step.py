"""Case I: steady laminar backward-facing-step separation benchmark."""

from __future__ import annotations
import math
import numpy as np
from fluent_field_export import export_npz_from_ascii
from fluent_mesh import backward_step_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_backward_step"; H=.01; U=1.; RHO=1.; RE=200.; MU=RHO*U*H/RE


def solve_bfs(tag:str,nx_up:int,nx_down:int,ny_up:int,ny_step:int,*,clean:bool=False)->dict:
    prefix=f"{CASE}_{tag}"
    if clean: clean_case(CASE)
    mesh=OUT/f"{prefix}.msh"; stats=backward_step_2d(mesh,h=H,nx_up=nx_up,nx_down=nx_down,ny_up=ny_up,ny_step=ny_step)
    raw=OUT/f"{prefix}_raw.csv"; npz=OUT/f"{prefix}_field.npz"
    with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
        s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.viscous.model="laminar"
        air=s.settings.setup.materials.fluid["air"]; air.density.value=RHO; air.viscosity.value=MU
        s.settings.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity_magnitude.value=U
        s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=900)
        allowed=list(s.fields.field_data.scalar_fields.allowed_values()); sx=next((f for f in ("x-wall-shear","wall-shear-x") if f in allowed),None)
        quantities=["x-coordinate","y-coordinate","x-velocity","y-velocity","pressure","velocity-magnitude"]+([sx] if sx else [])
        s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior","lower-wall","inlet","outlet"],delimiter="comma",quantities=quantities,location="node")
        s.settings.file.write_case_data(file_name=str(OUT/f"{prefix}.cas.h5"))
    rows=read_fluent_ascii_export(raw)
    check=export_npz_from_ascii(raw,npz,fields=["velocity_x","velocity_y","pressure"],metadata={"case":"I","tag":tag,"Re_h":RE,"units":{"coordinates":"m","velocity_x":"m/s","velocity_y":"m/s","pressure":"Pa"},"fluent_version":"261","solver":"steady pressure-based laminar"})
    wall={}
    for r in rows:
        if r["x-coordinate"]>=0 and abs(r["y-coordinate"])<1e-10: wall[round(r["x-coordinate"],12)]=r
    wr=sorted(wall.values(),key=lambda r:r["x-coordinate"])
    reattach=None
    if sx:
        for a,b in zip(wr,wr[1:]):
            if a[sx]<0<=b[sx] and a["x-coordinate"]>.2*H:
                frac=-a[sx]/max(b[sx]-a[sx],1e-30); reattach=a["x-coordinate"]+frac*(b["x-coordinate"]-a["x-coordinate"]); break
    # Robust backup based on near-wall x velocity zero crossing.
    if reattach is None:
        near=sorted([r for r in rows if 0<r["y-coordinate"]<.12*H and r["x-coordinate"]>0],key=lambda r:r["x-coordinate"])
        for a,b in zip(near,near[1:]):
            if a["x-velocity"]<0<=b["x-velocity"]:
                reattach=b["x-coordinate"]; break
    inlet={round(r["y-coordinate"],12):r for r in rows if abs(r["x-coordinate"]+4*H)<1e-10}
    outlet={round(r["y-coordinate"],12):r for r in rows if abs(r["x-coordinate"]-30*H)<1e-10}
    def flux(rs):
        q=sorted(rs.values(),key=lambda r:r["y-coordinate"]); return RHO*float(np.trapezoid([r["x-velocity"] for r in q],[r["y-coordinate"] for r in q]))
    # Fluent's nodal ASCII export omits shared boundary corner nodes on the
    # inlet surface.  Use the exact prescribed inlet flux; outlet is integrated.
    mi,mo=RHO*U*(2*H),flux(outlet); mass_error=abs(mo-mi)/max(abs(mi),1e-30)
    return {"tag":tag,"stats":stats,"rows":rows,"wall":wr,"shear_name":sx,"reattachment_m":reattach,"reattachment_h":reattach/H if reattach else None,"mass_in":mi,"mass_out":mo,"mass_error":mass_error,"npz_check":check,"files":[mesh,raw,npz,OUT/f"{prefix}.cas.h5"]}


def main()->int:
    payload=base_payload(CASE,"Case I: 2-D backward-facing-step separation")
    try:
        r=solve_bfs("medium",40,180,40,20,clean=True)
        wallrows=[{"x_over_h":x["x-coordinate"]/H,"wall_shear_pa":x.get(r["shear_name"],float("nan"))} for x in r["wall"]]
        csvp=write_csv(OUT/f"{CASE}_wall_shear.csv",list(wallrows[0]),wallrows)
        ssvg=svg_xy_plot(OUT/f"{CASE}_wall_shear.svg",[(x["x_over_h"],x["wall_shear_pa"]) for x in wallrows],title="Case I: downstream wall shear",xlabel="x/h",ylabel="tau_x (Pa)")
        vsvg=svg_field_map(OUT/f"{CASE}_velocity.svg",[(x["x-coordinate"]/H,x["y-coordinate"]/H,x["velocity-magnitude"]) for x in r["rows"]],title="Case I: backward-step velocity",xlabel="x/h",ylabel="y/h")
        psvg=svg_field_map(OUT/f"{CASE}_pressure.svg",[(x["x-coordinate"]/H,x["y-coordinate"]/H,x["pressure"]) for x in r["rows"]],title="Case I: backward-step pressure",xlabel="x/h",ylabel="y/h")
        checks={"reattachment_detected":r["reattachment_h"] is not None,"reattachment_in_benchmark_range":3.<(r["reattachment_h"] or 0)<9.,"mass_error_lt_2pct":r["mass_error"]<.02,"field_npz_valid":r["npz_check"]["valid"],"recirculation_present":any(x["x-velocity"]<0 for x in r["rows"] if 0<x["x-coordinate"]<8*H and x["y-coordinate"]<H)}
        payload.update({"model":{"Re_h":RE,"rho_kg_m3":RHO,"mu_pa_s":MU,"expansion_ratio":1.5,"steady_laminar":True},"mesh":{**r["stats"],"type":"structured quadrilateral"},"results":{"reattachment_length_h":r["reattachment_h"],"mass_flow_in_kg_m_s":r["mass_in"],"mass_flow_out_kg_m_s":r["mass_out"],"mass_imbalance_relative":r["mass_error"]},"benchmark":{"acceptance_reattachment_h":"3-9 broad smoke range at Re_h=200; definition-sensitive"},"checks":checks,"convergence":{"iterations_requested":900},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [*r["files"],csvp,ssvg,vsvg,psvg]]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
