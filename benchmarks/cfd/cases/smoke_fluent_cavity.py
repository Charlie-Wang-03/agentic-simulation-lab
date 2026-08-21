"""Case G: steady 2-D lid-driven cavity at Re=100 and 1000."""

from __future__ import annotations

import math
import numpy as np

from fluent_field_export import export_npz_from_ascii
from fluent_mesh import rectangular_2d
from fluent_smoke_common import OUT, base_payload, clean_case, fluent_session, read_fluent_ascii_export, svg_field_map, svg_xy_plot, write_csv, write_json

CASE="fluent_cavity"
RHO=1.0; U=1.0; L=1.0


def _nearest(rows, x, y):
    return min(rows,key=lambda r:(r["x-coordinate"]-x)**2+(r["y-coordinate"]-y)**2)


def run_re(session, re: int, raw, npz):
    air=session.settings.setup.materials.fluid["air"]
    air.density.value=RHO; air.viscosity.value=RHO*U*L/re
    session.settings.solution.initialization.hybrid_initialize()
    session.settings.solution.run_calculation.iterate(iter_count=1200 if re==1000 else 700)
    session.settings.file.export.ascii(
        file_name=str(raw),surface_name_list=["interior"],delimiter="comma",
        quantities=["x-coordinate","y-coordinate","x-velocity","y-velocity","pressure","velocity-magnitude"],location="node")
    rows=read_fluent_ascii_export(raw)
    unique={}
    for r in rows: unique[(round(r["x-coordinate"],12),round(r["y-coordinate"],12))]=r
    rows=list(unique.values())
    export=export_npz_from_ascii(raw,npz,fields=["velocity_x","velocity_y","pressure"],metadata={
        "case":"G","Re":re,"units":{"coordinates":"m","velocity_x":"m/s","velocity_y":"m/s","pressure":"Pa"},
        "fluent_version":"261","solver":"steady pressure-based laminar","converged":"iteration-limited smoke benchmark"})
    uline=[]; vline=[]
    for q in np.linspace(0,1,65):
        ru=_nearest(rows,0.5,float(q)); rv=_nearest(rows,float(q),0.5)
        uline.append((float(q),ru["x-velocity"])); vline.append((float(q),rv["y-velocity"]))
    candidates=[r for r in rows if .15<r["x-coordinate"]<.85 and .15<r["y-coordinate"]<.9]
    center=min(candidates,key=lambda r:r["velocity-magnitude"])
    # Ghia et al. centerline anchor values (interpolated benchmark table).
    refs={100:{"u_y_0.5":-0.2058,"v_x_0.5":0.0545,"center":(0.617,0.734)},
          1000:{"u_y_0.5":-0.0608,"v_x_0.5":0.0258,"center":(0.531,0.565)}}[re]
    uhalf=_nearest(rows,.5,.5)["x-velocity"]; vhalf=_nearest(rows,.5,.5)["y-velocity"]
    center_error=math.hypot(center["x-coordinate"]-refs["center"][0],center["y-coordinate"]-refs["center"][1])
    lower=[r for r in rows if r["y-coordinate"]<.15 and (.03<r["x-coordinate"]<.25 or .75<r["x-coordinate"]<.97)]
    secondary=any(r["x-velocity"]<0 for r in lower) and any(r["x-velocity"]>0 for r in lower)
    return {"Re":re,"rows":rows,"uline":uline,"vline":vline,"center":center,"center_error":center_error,
            "u_center":uhalf,"v_center":vhalf,"references":refs,"secondary_vortices_detected":secondary,"export":export}


def main()->int:
    clean_case(CASE)
    mesh=OUT/f"{CASE}.msh"; n=80
    coords=[0.5*(1-math.cos(math.pi*i/n)) for i in range(n+1)]
    stats=rectangular_2d(mesh,coords,coords,left=("left-wall","wall"),right=("right-wall","wall"),bottom=("bottom-wall","wall"),top=("lid","wall"))
    payload=base_payload(CASE,"Case G: 2-D steady lid-driven cavity")
    payload["mesh"]={**stats,"type":"cosine-clustered structured quadrilateral","nx":n,"ny":n}
    results=[]
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.viscous.model="laminar"
            lid=s.settings.setup.boundary_conditions.wall["lid"]
            lid.momentum.wall_motion="Moving Wall"; lid.momentum.velocity_spec="Components"
            lid.momentum.velocity_components[0].value=U; lid.momentum.velocity_components[1].value=0.0
            for re in (100,1000):
                results.append(run_re(s,re,OUT/f"{CASE}_re{re}_raw.csv",OUT/f"{CASE}_re{re}_field.npz"))
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}_re1000.cas.h5"))
        summaries=[]; checks={}
        files=[mesh,OUT/f"{CASE}_re1000.cas.h5"]
        for r in results:
            re=r["Re"]
            prof=[{"coordinate":a,"u_vertical_centerline":u,"v_horizontal_centerline":v} for (a,u),(_,v) in zip(r["uline"],r["vline"])]
            csvp=write_csv(OUT/f"{CASE}_re{re}_centerlines.csv",list(prof[0]),prof)
            usvg=svg_xy_plot(OUT/f"{CASE}_re{re}_u_centerline.svg",r["uline"],title=f"Case G Re={re}: vertical centerline u",xlabel="y/L",ylabel="u/U")
            vsvg=svg_field_map(OUT/f"{CASE}_re{re}_velocity.svg",[(x["x-coordinate"],x["y-coordinate"],x["velocity-magnitude"]) for x in r["rows"]],title=f"Case G Re={re}: velocity magnitude")
            files += [csvp,usvg,vsvg,OUT/f"{CASE}_re{re}_raw.csv",OUT/f"{CASE}_re{re}_field.npz"]
            c={"field_npz_valid":r["export"]["valid"],"main_vortex_location_within_0p18L":r["center_error"]<.18,
               "centerline_u_reasonable":abs(r["u_center"]-r["references"]["u_y_0.5"])<.18,
               "finite_pressure":all(math.isfinite(x["pressure"]) for x in r["rows"])}
            checks[f"Re_{re}"]=c
            summaries.append({"Re":re,"main_vortex_x":r["center"]["x-coordinate"],"main_vortex_y":r["center"]["y-coordinate"],"center_error_L":r["center_error"],"u_at_center":r["u_center"],"v_at_center":r["v_center"],"secondary_vortices_detected":r["secondary_vortices_detected"],"field_nodes":len(r["rows"])})
        passed=all(all(x.values()) for x in checks.values())
        payload.update({"model":{"rho_kg_m3":RHO,"lid_velocity_m_s":U,"Re":[100,1000],"steady_laminar":True},"results":summaries,"benchmark":{"source":"Ghia et al. centerline/main-vortex reference values","acceptance":"broad smoke-level centerline and vortex-location checks"},"checks":checks,"convergence":{"iterations":{"Re100":700,"Re1000":1200}},"status":"PASS" if passed else "FAIL","files":[str(x.resolve()) for x in files]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
