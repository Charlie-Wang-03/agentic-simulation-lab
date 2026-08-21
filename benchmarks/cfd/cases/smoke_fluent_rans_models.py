"""Case M: realizable k-epsilon vs k-omega SST on a turbulent backward step."""
from __future__ import annotations
import math
import numpy as np
from fluent_mesh import backward_step_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_rans_models"; H=.01; U=10.; RHO=1.; RE=5000.; MU=RHO*U*H/RE
def pick(allowed,*names): return next((x for x in names if x in allowed),None)

def analyse(raw,model,fields,stats):
    rows=read_fluent_ascii_export(raw); sx=fields["wall_shear"]; yp=fields["yplus"]
    wall={round(r["x-coordinate"],12):r for r in rows if r["x-coordinate"]>=0 and abs(r["y-coordinate"])<1e-10}; wr=sorted(wall.values(),key=lambda r:r["x-coordinate"])
    xr=None
    if sx:
        for a,b in zip(wr,wr[1:]):
            if a.get(sx,0)<0<=b.get(sx,0) and a["x-coordinate"]>.2*H:
                f=-a[sx]/max(b[sx]-a[sx],1e-30); xr=(a["x-coordinate"]+f*(b["x-coordinate"]-a["x-coordinate"]))/H; break
    yplus=[r.get(yp,0) for r in wr] if yp else []
    prof={}
    for r in rows:
        if abs(r["x-coordinate"]-10*H)<.3*H: prof[round(r["y-coordinate"],12)]=r
    pr=sorted(prof.values(),key=lambda r:r["y-coordinate"])
    return {"model":model,"reattachment_h":xr,"wall_yplus_mean":float(np.mean(yplus)) if yplus else None,"wall_yplus_max":max(yplus) if yplus else None,"profile":pr,"wall":wr,"rows":rows,"fields":fields,"mesh":stats}

def main()->int:
    clean_case(CASE); mesh=OUT/f"{CASE}.msh"; stats=backward_step_2d(mesh,h=H,nx_up=40,nx_down=200,ny_up=48,ny_step=24)
    payload=base_payload(CASE,"Case M: RANS model and near-wall treatment comparison")
    results=[]; files=[mesh]
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); air=s.settings.setup.materials.fluid["air"]; air.density.value=RHO; air.viscosity.value=MU
            vin=s.settings.setup.boundary_conditions.velocity_inlet["inlet"]; vin.momentum.velocity_magnitude.value=U; vin.turbulence.turbulent_intensity=.05; vin.turbulence.turbulent_viscosity_ratio=10.
            for name,model in (("realizable_ke","realizable k-epsilon"),("sst","k-omega SST")):
                if name=="realizable_ke":
                    s.settings.setup.models.viscous.model="k-epsilon"; s.settings.setup.models.viscous.k_epsilon_model="realizable"; s.settings.setup.models.viscous.near_wall_treatment.wall_treatment="enhanced-wall-treatment"
                else:
                    s.settings.setup.models.viscous.model="k-omega"; s.settings.setup.models.viscous.k_omega_model="sst"
                s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=900)
                allowed=list(s.fields.field_data.scalar_fields.allowed_values()); fields={"wall_shear":pick(allowed,"x-wall-shear","wall-shear-x"),"yplus":pick(allowed,"wall-yplus","y-plus","yplus"),"k":pick(allowed,"turb-kinetic-energy","turbulent-kinetic-energy"),"omega":pick(allowed,"specific-diss-rate"),"epsilon":pick(allowed,"turb-diss-rate")}
                qs=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity","velocity-magnitude"]+[x for x in fields.values() if x]
                raw=OUT/f"{CASE}_{name}_raw.csv"; s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior","lower-wall"],delimiter="comma",quantities=qs,location="node"); s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}_{name}.cas.h5"))
                results.append(analyse(raw,model,fields,stats)); files += [raw,OUT/f"{CASE}_{name}.cas.h5"]
        summary=[]
        for r in results:
            summary.append({k:r[k] for k in ("model","reattachment_h","wall_yplus_mean","wall_yplus_max")})
            slug="ke" if "epsilon" in r["model"] else "sst"; pcsv=write_csv(OUT/f"{CASE}_{slug}_profile.csv",["y_over_h","u_over_uin"],[{"y_over_h":x["y-coordinate"]/H,"u_over_uin":x["x-velocity"]/U} for x in r["profile"]]); files.append(pcsv)
            kf=r["fields"]["k"]
            if kf: files.append(svg_field_map(OUT/f"{CASE}_{slug}_tke.svg",[(x["x-coordinate"]/H,x["y-coordinate"]/H,x.get(kf,0)) for x in r["rows"]],title=f"Case M {r['model']}: turbulent kinetic energy",xlabel="x/h",ylabel="y/h"))
        comp=write_csv(OUT/f"{CASE}_comparison.csv",list(summary[0]),summary); files.append(comp)
        profsvg=svg_xy_plot(OUT/f"{CASE}_velocity_profiles.svg",[(x["y-coordinate"]/H,x["x-velocity"]/U) for x in results[0]["profile"]],title="Case M: velocity at x/h=10",xlabel="y/h",ylabel="u/U",reference=[(x["y-coordinate"]/H,x["x-velocity"]/U) for x in results[1]["profile"]]); files.append(profsvg)
        checks={"both_reattachment_detected":all(r["reattachment_h"] for r in results),"reattachment_in_broad_range":all(3<r["reattachment_h"]<12 for r in results),"yplus_exported":all(r["wall_yplus_max"] is not None for r in results),"wall_shear_exported":all(r["fields"]["wall_shear"] for r in results),"tke_exported":all(r["fields"]["k"] for r in results),"model_specific_dissipation_exported":bool(results[0]["fields"]["epsilon"] and results[1]["fields"]["omega"]),"finite_results":all(math.isfinite(r["reattachment_h"]) for r in results)}
        payload.update({"model":{"Re_h":RE,"models":["realizable k-epsilon + enhanced wall treatment","k-omega SST"]},"mesh":{**stats,"type":"structured quadrilateral"},"results":summary,"checks":checks,"convergence":{"iterations_requested_per_model":900},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in files]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
