"""Case B: 3-D turbulent circular-pipe smoke benchmark."""

from __future__ import annotations

import math
import numpy as np

from fluent_mesh import pipe_3d
from fluent_smoke_common import OUT, base_payload, clean_case, fluent_session, read_fluent_ascii_export, rel_error, svg_xy_plot, write_csv, write_json

CASE="fluent_turbulent_pipe"
D=0.020
L=1.0
U=15.0
RHO=1.225
MU=1.7894e-5

def main()->int:
    clean_case(CASE)
    mesh=OUT/f"{CASE}.msh"
    mesh_stats=pipe_3d(mesh,diameter=D,length=L,nxy=12,nx=80)
    payload=base_payload(CASE,"3-D steady turbulent pipe flow")
    payload["model"]={"fluid":"air","rho_kg_m3":RHO,"mu_pa_s":MU,"diameter_m":D,"length_m":L,"bulk_velocity_m_s":U,"turbulence_model":"k-omega SST"}
    payload["mesh"]={**mesh_stats,"type":"mapped square-to-circle hexahedral","cross_section":"12x12","axial":80}
    try:
        with fluent_session(dimension=3,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh))
            s.settings.setup.models.viscous.model="k-omega"
            if hasattr(s.settings.setup.models.viscous,"k_omega_model"): s.settings.setup.models.viscous.k_omega_model="sst"
            air=s.settings.setup.materials.fluid["air"]
            air.density.value=RHO; air.viscosity.value=MU
            inlet=s.settings.setup.boundary_conditions.velocity_inlet["inlet"]
            inlet.momentum.velocity_magnitude.value=1.0
            inlet.turbulence.turbulent_intensity=0.05
            inlet.turbulence.turbulent_viscosity_ratio=10.0
            stations=[]
            for index,xstation in enumerate(np.linspace(0.55,0.95,9)):
                name=f"station-{index:02d}"; stations.append(name)
                s.settings.results.surfaces.plane_slice[name]={"normal":[1.0,0.0,0.0],"distance_from_origin":float(xstation)}
            s.settings.solution.methods.p_v_coupling.flow_scheme="SIMPLE"
            disc=s.settings.solution.methods.spatial_discretization.discretization_scheme
            disc["mom"]="first-order-upwind"; disc["k"]="first-order-upwind"; disc["omega"]="first-order-upwind"
            s.settings.solution.initialization.hybrid_initialize()
            s.settings.solution.run_calculation.iterate(iter_count=120)
            inlet.momentum.velocity_magnitude.value=5.0
            s.settings.solution.run_calculation.iterate(iter_count=180)
            inlet.momentum.velocity_magnitude.value=U
            s.settings.solution.run_calculation.iterate(iter_count=600)
            available=list(s.fields.field_data.scalar_fields.allowed_values())
            wall_field=next((f for f in ("wall-shear","wall-shear-stress","x-wall-shear") if f in available),None)
            print("WALL_FIELD",wall_field)
            quantities=["x-coordinate","y-coordinate","z-coordinate","pressure","x-velocity","velocity-magnitude"]
            if wall_field: quantities.append(wall_field)
            raw=OUT/f"{CASE}_raw.csv"
            integrals=s.settings.results.report.surface_integrals
            mdot_in_native=abs(float(integrals.get_mass_flow_rate(surface_names=["inlet"])["inlet"]))
            mdot_out_native=abs(float(integrals.get_mass_flow_rate(surface_names=["outlet"])["outlet"]))
            outlet_mean_native=float(integrals.get_area_weighted_avg(surface_names=["outlet"],report_of="x-velocity")["outlet"])
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
            s.settings.file.export.ascii(file_name=str(raw),surface_name_list=stations+["outlet","pipe-wall"],delimiter="comma",quantities=quantities,location="node")
        rows=read_fluent_ascii_export(raw)
        # Axial pressure is averaged at each structured x station.
        buckets={}
        for r in rows:
            x=round(r["x-coordinate"],8)
            if x>=0.55*L and math.hypot(r.get("y-coordinate",0),r.get("z-coordinate",0))<0.49*D:
                buckets.setdefault(x,[]).append(r["pressure"])
        axial=sorted((x,float(np.mean(v))) for x,v in buckets.items() if len(v)>20)
        slope,intercept=np.polyfit([x for x,_ in axial],[p for _,p in axial],1)
        dpdx=-float(slope)
        re=RHO*U*D/MU
        f_fluent=dpdx*2*D/(RHO*U**2)
        f_blasius=0.3164/re**0.25
        dp_full=dpdx*L
        tau_from_gradient=dpdx*D/4
        wall_rows=[r for r in rows if 0.55*L<r["x-coordinate"]<0.95*L and abs(math.hypot(r.get("y-coordinate",0),r.get("z-coordinate",0))-D/2)<2e-5]
        if wall_field and wall_rows:
            tau_wall=float(np.mean([abs(r[wall_field]) for r in wall_rows]))
        else:
            tau_wall=tau_from_gradient
        outlet_rows=[r for r in rows if abs(r["x-coordinate"]-L)<1e-8]
        # Area-weight the mapped 12x12 outlet quads; an unweighted nodal mean
        # overweights the no-slip circumference and is not a bulk velocity.
        node={(round(r["y-coordinate"],9),round(r["z-coordinate"],9)):r["x-velocity"] for r in outlet_rows}
        uv=[-1+2*i/12 for i in range(13)]
        def mapped(u,v):
            if abs(u)<1e-15 and abs(v)<1e-15:return (0.0,0.0)
            if abs(u)>abs(v): rr,th=u,math.pi/4*v/u
            else: rr,th=v,math.pi/2-math.pi/4*u/v
            return (D/2*rr*math.cos(th),D/2*rr*math.sin(th))
        pts=[[mapped(u,v) for u in uv] for v in uv]; flux=area_sum=0.0
        for j in range(12):
            for i in range(12):
                q=[pts[j][i],pts[j][i+1],pts[j+1][i+1],pts[j+1][i]]
                area=abs(sum(q[k][0]*q[(k+1)%4][1]-q[(k+1)%4][0]*q[k][1] for k in range(4)))/2
                vel=sum(node[(round(y,9),round(z,9))] for y,z in q)/4
                flux+=area*vel; area_sum+=area
        outlet_mean_nodal=flux/area_sum
        outlet_mean=outlet_mean_native
        mdot_theory=RHO*U*math.pi*D**2/4
        mass_balance=abs(mdot_in_native-mdot_out_native)/mdot_in_native
        results={"pressure_gradient_pa_m":dpdx,"pressure_drop_extrapolated_pa":dp_full,"mean_velocity_outlet_area_weighted_m_s":outlet_mean,"nodal_quadrature_velocity_m_s":outlet_mean_nodal,"reynolds_number":re,"wall_shear_stress_pa":tau_wall,"darcy_friction_factor":f_fluent,"mass_flow_inlet_kg_s":mdot_in_native,"mass_flow_outlet_kg_s":mdot_out_native,"mass_balance_relative":mass_balance}
        theory={"blasius_darcy_friction_factor":f_blasius,"darcy_weisbach_pressure_drop_pa":f_blasius*(L/D)*RHO*U**2/2,"wall_shear_from_dpdx_pa":tau_from_gradient}
        errors={"friction_factor_relative":rel_error(f_fluent,f_blasius),"wall_shear_balance_relative":rel_error(tau_wall,tau_from_gradient),"outlet_mean_relative":rel_error(outlet_mean,U)}
        checks={"re_turbulent":re>10000,"friction_factor_error_lt_30pct":errors["friction_factor_relative"]<0.30,"wall_shear_balance_lt_35pct":errors["wall_shear_balance_relative"]<0.35,"mean_velocity_error_lt_2pct":errors["outlet_mean_relative"]<0.02,"mass_balance_lt_1pct":mass_balance<0.01,"mass_flow_theory_lt_1pct":rel_error(mdot_out_native,mdot_theory)<0.01}
        csv=write_csv(OUT/f"{CASE}_axial_pressure.csv",["x_m","mean_pressure_pa"],[{"x_m":x,"mean_pressure_pa":p} for x,p in axial])
        svg=svg_xy_plot(OUT/f"{CASE}_axial_pressure.svg",axial,title="Case B: developed axial pressure",xlabel="x (m)",ylabel="gauge pressure (Pa)")
        payload.update({"results":results,"theory":theory,"errors":errors,"checks":checks,"convergence":{"iterations_requested":600,"fluent_auto_stop":True},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(p.resolve()) for p in (mesh,raw,csv,svg,OUT/f"{CASE}.cas.h5")]})
    except Exception as exc:
        payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload)
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
