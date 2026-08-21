"""Case J: automated NACA 0012 angle-of-attack sweep."""
from __future__ import annotations
import math
import numpy as np
from fluent_field_export import export_npz_from_ascii
from fluent_mesh import naca0012_ogrid_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_airfoil"; RHO=1.225; U=10.; C=1.; RE=2e5; MU=RHO*U*C/RE; AOAS=(-5,0,5,10)

def solve_aoa(a):
    tag=f"a{a:+d}".replace("+","p").replace("-","m"); mesh=OUT/f"{CASE}_{tag}.msh"
    stats=naca0012_ogrid_2d(mesh,angle_deg=a,nr=48,nt=180,far=15.)
    raw=OUT/f"{CASE}_{tag}_raw.csv"; surface_raw=OUT/f"{CASE}_{tag}_surface_raw.csv"
    with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
        s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.viscous.model="k-omega"
        if hasattr(s.settings.setup.models.viscous,"k_omega_model"): s.settings.setup.models.viscous.k_omega_model="sst"
        air=s.settings.setup.materials.fluid["air"]; air.density.value=RHO; air.viscosity.value=MU
        vin=s.settings.setup.boundary_conditions.velocity_inlet["inlet"]; vin.momentum.velocity_magnitude.value=U
        vin.turbulence.turbulent_intensity=.01; vin.turbulence.turbulent_viscosity_ratio=5.
        s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=700)
        allowed=list(s.fields.field_data.scalar_fields.allowed_values()); sx=next((f for f in ("x-wall-shear","wall-shear-x") if f in allowed),None); sy=next((f for f in ("y-wall-shear","wall-shear-y") if f in allowed),None)
        qs=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity","velocity-magnitude"]+[q for q in (sx,sy) if q]
        s.settings.file.export.ascii(file_name=str(surface_raw),surface_name_list=["airfoil"],delimiter="comma",quantities=qs,location="node")
        s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior"],delimiter="comma",quantities=qs,location="node")
        s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}_{tag}.cas.h5"))
    rows=read_fluent_ascii_export(raw); surf={}
    for r in read_fluent_ascii_export(surface_raw): surf[(round(r["x-coordinate"],9),round(r["y-coordinate"],9))]=r
    alpha=-math.radians(a)
    def body(r):
        dx=r["x-coordinate"]-.25; y=r["y-coordinate"]
        return .25+dx*math.cos(alpha)+y*math.sin(alpha),-dx*math.sin(alpha)+y*math.cos(alpha)
    sr=sorted(surf.values(),key=lambda r:math.atan2(body(r)[1],body(r)[0]-.25))
    fx=fy=0.; cp_rows=[]; qdyn=.5*RHO*U*U
    for i,r in enumerate(sr):
        b=sr[(i+1)%len(sr)]; dx=b["x-coordinate"]-r["x-coordinate"]; dy=b["y-coordinate"]-r["y-coordinate"]; ds=math.hypot(dx,dy); pm=.5*(r["pressure"]+b["pressure"])
        fx += -pm*dy; fy += pm*dx
        if sx: fx += .5*(r.get(sx,0)+b.get(sx,0))*ds
        if sy: fy += .5*(r.get(sy,0)+b.get(sy,0))*ds
        xb,yb=body(r); cp_rows.append({"aoa_deg":a,"x_over_c":xb,"surface":"upper" if yb>=0 else "lower","cp":r["pressure"]/qdyn,"pressure_pa":r["pressure"]})
    cd=fx/(qdyn*C); cl=fy/(qdyn*C)
    npz=OUT/f"{CASE}_{tag}_field.npz"; check=export_npz_from_ascii(raw,npz,fields=["velocity_x","velocity_y","pressure"],metadata={"case":"J","airfoil":"NACA0012","aoa_deg":a,"Re":RE,"units":{"coordinates":"m","velocity_x":"m/s","velocity_y":"m/s","pressure":"Pa"},"fluent_version":"261","solver":"steady pressure-based k-omega SST"})
    return {"aoa":a,"cl":cl,"cd":cd,"ld":cl/cd if abs(cd)>1e-12 else None,"cp":cp_rows,"rows":rows,"stats":stats,"check":check,"files":[mesh,raw,surface_raw,npz,OUT/f"{CASE}_{tag}.cas.h5"]}

def main()->int:
    clean_case(CASE); payload=base_payload(CASE,"Case J: 2-D NACA 0012 aerodynamic AoA sweep")
    try:
        rr=[solve_aoa(a) for a in AOAS]; curve=[{"aoa_deg":r["aoa"],"cl":r["cl"],"cd":r["cd"],"cl_over_cd":r["ld"]} for r in rr]
        curve_csv=write_csv(OUT/f"{CASE}_polar.csv",list(curve[0]),curve); cpall=[x for r in rr for x in r["cp"]]; cp_csv=write_csv(OUT/f"{CASE}_cp.csv",list(cpall[0]),cpall)
        clsvg=svg_xy_plot(OUT/f"{CASE}_cl_aoa.svg",[(x["aoa_deg"],x["cl"]) for x in curve],title="Case J: NACA 0012 lift curve",xlabel="AoA (deg)",ylabel="Cl")
        cdsvg=svg_xy_plot(OUT/f"{CASE}_cd_aoa.svg",[(x["aoa_deg"],x["cd"]) for x in curve],title="Case J: NACA 0012 drag polar",xlabel="AoA (deg)",ylabel="Cd")
        cp5=next(r for r in rr if r["aoa"]==5); cpsvg=svg_xy_plot(OUT/f"{CASE}_cp_a5.svg",[(x["x_over_c"],x["cp"]) for x in cp5["cp"] if x["surface"]=="upper"],title="Case J: Cp at AoA=5 deg",xlabel="x/c",ylabel="Cp",reference=[(x["x_over_c"],x["cp"]) for x in cp5["cp"] if x["surface"]=="lower"])
        last=rr[-1]; vsvg=svg_field_map(OUT/f"{CASE}_velocity_a10.svg",[(x["x-coordinate"],x["y-coordinate"],x["velocity-magnitude"]) for x in last["rows"]],title="Case J: velocity field at 10 deg")
        cls=[x["cl"] for x in curve]; slope=(cls[2]-cls[0])/math.radians(10)
        checks={"all_fields_valid":all(r["check"]["valid"] for r in rr),"lift_monotonic":all(b>a for a,b in zip(cls,cls[1:])),"zero_aoa_lift_near_zero":abs(cls[1])<.15,"lift_slope_reasonable":3.<slope<9.,"all_drag_positive":all(0<x["cd"]<1 for x in curve),"finite_results":all(math.isfinite(x["cl"]) and math.isfinite(x["cd"]) for x in curve)}
        files=[curve_csv,cp_csv,clsvg,cdsvg,cpsvg,vsvg,*[p for r in rr for p in r["files"]]]
        payload.update({"model":{"airfoil":"NACA 0012","AoA_deg":list(AOAS),"Re_c":RE,"velocity_m_s":U,"turbulence_model":"k-omega SST"},"mesh":{**rr[0]["stats"],"type":"mapped O-grid","radial":48,"circumferential":180},"results":{"polar":curve,"lift_curve_slope_per_rad":slope},"benchmark":{"thin_airfoil_slope_per_rad":2*math.pi,"scope":"automation benchmark, not wind-tunnel-grade wall-resolved validation"},"checks":checks,"convergence":{"iterations_requested_per_aoa":700},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in files]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
