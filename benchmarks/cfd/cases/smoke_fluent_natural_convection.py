"""Case E: differentially heated square-cavity natural convection."""
from __future__ import annotations
import math
import numpy as np
from fluent_mesh import rectangular_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,svg_field_map,write_csv,write_json

CASE="fluent_natural_convection"; L=0.1; TH=310.0; TC=290.0
RHO=1.177; MU=1.846e-5; K=0.0263; CP=1007.0; BETA=1/300.0; G=9.81

def set_property(obj,names,value):
    for name in names:
        if name in getattr(obj,"child_names",[]):
            child=getattr(obj,name)
            if "value" in getattr(child,"child_names",[]): child.value=value
            else: child.set_state(value)
            print("SET_PROPERTY",name,value); return name
    raise RuntimeError(f"None of {names} found in {getattr(obj,'child_names',[])}")

def main()->int:
    clean_case(CASE); mesh=OUT/f"{CASE}.msh"; coords=[L*i/50 for i in range(51)]
    stats=rectangular_2d(mesh,coords,coords,left=("hot-wall","wall"),right=("cold-wall","wall"),bottom=("bottom-adiabatic","wall"),top=("top-adiabatic","wall"))
    nu=MU/RHO; alpha=K/(RHO*CP); ra=G*BETA*(TH-TC)*L**3/(nu*alpha)
    payload=base_payload(CASE,"2-D steady Boussinesq natural convection")
    payload["model"]={"fluid":"air","hot_wall_K":TH,"cold_wall_K":TC,"gravity_m_s2":[0,-G],"density_model":"Boussinesq","rayleigh_number":ra,"prandtl_number":nu/alpha}
    payload["mesh"]={**stats,"type":"uniform quadrilateral","nx":50,"ny":50}
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.viscous.model="laminar"; s.settings.setup.models.energy.enabled=True
            grav=s.settings.setup.general.operating_conditions.gravity; grav.enable=True; grav.components=[0.0,-G,0.0]
            air=s.settings.setup.materials.fluid["air"]
            air.viscosity.value=MU; air.thermal_conductivity.value=K; air.specific_heat.value=CP
            air.density.option="boussinesq"
            set_property(air.density,["boussinesq_density","reference_density","rho0","value"],RHO)
            set_property(air,["therm_exp_coeff","thermal_expansion_coefficient"],BETA)
            for name,temp in (("hot-wall",TH),("cold-wall",TC)):
                wall=s.settings.setup.boundary_conditions.wall[name]; wall.thermal.thermal_condition="Temperature"; wall.thermal.temperature.value=temp
            for name in ("top-adiabatic","bottom-adiabatic"):
                wall=s.settings.setup.boundary_conditions.wall[name]; wall.thermal.thermal_condition="Heat Flux"; wall.thermal.heat_flux.value=0.0
            s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=1200)
            allowed=list(s.fields.field_data.scalar_fields.allowed_values()); qfield=next((f for f in ("wall-heat-flux","surface-heat-flux","heat-flux") if f in allowed),None); print("HEAT_FLUX_FIELD",qfield)
            quantities=["x-coordinate","y-coordinate","temperature","x-velocity","y-velocity","velocity-magnitude"]+([qfield] if qfield else [])
            raw=OUT/f"{CASE}_raw.csv"; s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior","hot-wall"],delimiter="comma",quantities=quantities,location="node")
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        rows=read_fluent_ascii_export(raw); hot=[r for r in rows if abs(r["x-coordinate"])<1e-9]
        qavg=float(np.mean([abs(r[qfield]) for r in hot])) if qfield else float("nan"); nusselt=qavg*L/(K*(TH-TC))
        interior=[r for r in rows if 0<r["x-coordinate"]<L and 0<r["y-coordinate"]<L]
        vmax=max(r["velocity-magnitude"] for r in interior)
        field_rows=[{"x_m":r["x-coordinate"],"y_m":r["y-coordinate"],"temperature_K":r["temperature"],"velocity_m_s":r["velocity-magnitude"]} for r in interior]
        csv=write_csv(OUT/f"{CASE}_field_data.csv",list(field_rows[0]),field_rows)
        tsvg=svg_field_map(OUT/f"{CASE}_temperature_field.svg",[(r["x_m"],r["y_m"],r["temperature_K"]) for r in field_rows],title="Case E: cavity temperature field")
        vsvg=svg_field_map(OUT/f"{CASE}_velocity_field.svg",[(r["x_m"],r["y_m"],r["velocity_m_s"]) for r in field_rows],title="Case E: buoyancy-driven velocity magnitude")
        checks={"rayleigh_in_benchmark_range":1e5<ra<1e7,"temperature_bounded":min(r["temperature"] for r in interior)>=TC-1 and max(r["temperature"] for r in interior)<=TH+1,"flow_developed":vmax>1e-3,"nusselt_benchmark_range":5<nusselt<15}
        payload.update({"results":{"rayleigh_number":ra,"prandtl_number":nu/alpha,"maximum_velocity_m_s":vmax,"hot_wall_mean_heat_flux_w_m2":qavg,"hot_wall_average_nusselt":nusselt},"benchmark":{"expected_Nu_range_for_Ra_order_1e6":"approximately 7-12; acceptance 5-15"},"checks":checks,"convergence":{"iterations_requested":1200},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(p.resolve()) for p in (mesh,raw,csv,tsvg,vsvg,OUT/f"{CASE}.cas.h5")]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
