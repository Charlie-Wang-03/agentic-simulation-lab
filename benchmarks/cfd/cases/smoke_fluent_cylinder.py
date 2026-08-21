"""Case C: steady 2-D laminar flow around a circular cylinder at Re=40."""

from __future__ import annotations
import math
import numpy as np
from fluent_mesh import cylinder_ogrid_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_cylinder"; D=1.0; R=0.5; U=1.0; RHO=1.0; MU=0.025

def main()->int:
    clean_case(CASE); mesh=OUT/f"{CASE}.msh"
    stats=cylinder_ogrid_2d(mesh,radius=R,half_length=15.0,half_height=10.0,nr=64,nt=160)
    payload=base_payload(CASE,"2-D steady laminar cylinder external flow")
    payload["model"]={"fluid":"constant-property benchmark fluid","rho_kg_m3":RHO,"mu_pa_s":MU,"diameter_m":D,"velocity_m_s":U,"reynolds_number":RHO*U*D/MU,"regime":"steady symmetric wake"}
    payload["mesh"]={**stats,"type":"mapped O-grid quadrilateral","radial":64,"circumferential":160,"domain":"x=+-15D, y=+-10D"}
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.viscous.model="laminar"
            air=s.settings.setup.materials.fluid["air"]; air.density.value=RHO; air.viscosity.value=MU
            s.settings.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity_magnitude.value=U
            s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=700)
            available=list(s.fields.field_data.scalar_fields.allowed_values())
            shear_x=next((f for f in ("x-wall-shear","wall-shear-x") if f in available),None)
            shear_y=next((f for f in ("y-wall-shear","wall-shear-y") if f in available),None)
            quantities=["x-coordinate","y-coordinate","pressure","x-velocity","y-velocity","velocity-magnitude"]+[f for f in (shear_x,shear_y) if f]
            raw=OUT/f"{CASE}_raw.csv"
            s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["cylinder","interior"],delimiter="comma",quantities=quantities,location="node")
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        rows=read_fluent_ascii_export(raw)
        cyl={}
        for r in rows:
            rr=math.hypot(r["x-coordinate"],r["y-coordinate"])
            if abs(rr-R)<1e-6:
                cyl[(round(r["x-coordinate"],9),round(r["y-coordinate"],9))]=r
        surf=sorted(cyl.values(),key=lambda r:math.atan2(r["y-coordinate"],r["x-coordinate"]))
        theta=np.unwrap(np.asarray([math.atan2(r["y-coordinate"],r["x-coordinate"]) for r in surf]))
        p=np.asarray([r["pressure"] for r in surf]); q=0.5*RHO*U**2
        th=np.r_[theta,theta[0]+2*math.pi]; pp=np.r_[p,p[0]]
        fx_p=float(np.trapezoid(-pp*np.cos(th)*R,th)); fy_p=float(np.trapezoid(-pp*np.sin(th)*R,th))
        fx_s=fy_s=0.0
        if shear_x:
            sx=np.asarray([r.get(shear_x,0.0) for r in surf]); fx_s=float(np.trapezoid(np.r_[sx,sx[0]]*R,th))
        if shear_y:
            sy=np.asarray([r.get(shear_y,0.0) for r in surf]); fy_s=float(np.trapezoid(np.r_[sy,sy[0]]*R,th))
        cd=(fx_p+fx_s)/(q*D); cl=(fy_p+fy_s)/(q*D)
        cp=p/q
        field=[(r["x-coordinate"],r["y-coordinate"],r["velocity-magnitude"]) for r in rows if math.hypot(r["x-coordinate"],r["y-coordinate"])>R*1.001]
        wake=[r for r in rows if r["x-coordinate"]>R and abs(r["y-coordinate"])<0.035]
        wake.sort(key=lambda r:r["x-coordinate"])
        pressure_rows=[{"theta_deg":float(t*180/math.pi),"pressure_pa":float(pi),"cp":float(ci)} for t,pi,ci in zip(theta,p,cp)]
        csv=write_csv(OUT/f"{CASE}_surface_pressure.csv",list(pressure_rows[0]),pressure_rows)
        wake_csv=write_csv(OUT/f"{CASE}_wake.csv",["x_m","velocity_m_s"],[{"x_m":r["x-coordinate"],"velocity_m_s":r["velocity-magnitude"]} for r in wake])
        psvg=svg_xy_plot(OUT/f"{CASE}_pressure_distribution.svg",[(r["theta_deg"],r["cp"]) for r in pressure_rows],title="Case C: cylinder pressure coefficient",xlabel="theta (deg)",ylabel="Cp")
        vsvg=svg_field_map(OUT/f"{CASE}_velocity_field.svg",field,title="Case C: velocity magnitude and wake")
        checks={"re_equals_40":abs(RHO*U*D/MU-40)<1e-9,"classic_cd_range":0.8<cd<2.2,"lift_near_zero":abs(cl)<0.12,"wake_deficit_visible":min((r["velocity-magnitude"] for r in wake),default=U)<0.8*U}
        payload.update({"results":{"drag_coefficient":cd,"lift_coefficient":cl,"pressure_drag_coefficient":fx_p/(q*D),"viscous_drag_coefficient":fx_s/(q*D),"minimum_wake_velocity_m_s":min(r["velocity-magnitude"] for r in wake)},"benchmark":{"Re":40,"expected_Cd_approx":"1.4-1.7; broad mesh acceptance 0.8-2.2","expected_Cl":0.0,"steady_no_strouhal":True},"checks":checks,"convergence":{"iterations_requested":700,"steady":True},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in (mesh,raw,csv,wake_csv,psvg,vsvg,OUT/f"{CASE}.cas.h5")]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
