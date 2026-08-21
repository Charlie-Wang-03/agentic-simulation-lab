"""Case F: 2-D compressible converging-diverging nozzle."""
from __future__ import annotations
import math
import numpy as np
from fluent_mesh import nozzle_2d
from fluent_smoke_common import OUT,base_payload,clean_case,fluent_session,read_fluent_ascii_export,rel_error,svg_field_map,svg_xy_plot,write_csv,write_json

CASE="fluent_compressible_nozzle"; L=1.0; XT=.4; HI=.05; HT=.02; HE=.04
P0=200000.0; T0=300.0; GAMMA=1.4; RGAS=287.0; RHO=1.225; MU=1.7894e-5

def area_ratio(m): return (1/m)*((2/(GAMMA+1)*(1+(GAMMA-1)*m*m/2))**((GAMMA+1)/(2*(GAMMA-1))))
def supersonic_mach(ar):
    lo,hi=1.000001,6.0
    for _ in range(100):
        mid=(lo+hi)/2
        if area_ratio(mid)<ar: lo=mid
        else: hi=mid
    return (lo+hi)/2

def main()->int:
    clean_case(CASE); mesh=OUT/f"{CASE}.msh"; stats=nozzle_2d(mesh,length=L,throat_x=XT,inlet_half_height=HI,throat_half_height=HT,exit_half_height=HE,nx=180,ny=30)
    ar=HE/HT; mex=supersonic_mach(ar); pexit=P0*(1+(GAMMA-1)*mex*mex/2)**(-GAMMA/(GAMMA-1)); pstar=P0*(2/(GAMMA+1))**(GAMMA/(GAMMA-1)); astar=2*HT
    mdot_star=P0*astar*math.sqrt(GAMMA/(RGAS*T0))*(2/(GAMMA+1))**((GAMMA+1)/(2*(GAMMA-1)))
    payload=base_payload(CASE,"2-D steady compressible C-D nozzle")
    payload["model"]={"fluid":"ideal-gas air","energy":True,"total_pressure_pa":P0,"total_temperature_K":T0,"back_pressure_pa":pexit,"exit_to_throat_area_ratio":ar}
    payload["mesh"]={**stats,"type":"structured body-fitted quadrilateral","nx":180,"ny":30}
    try:
        with fluent_session(dimension=2,processor_count=1,cwd=OUT) as s:
            s.settings.file.read_mesh(file_name=str(mesh)); s.settings.setup.models.energy.enabled=True; s.settings.setup.models.viscous.model="laminar"
            s.settings.setup.general.operating_conditions.operating_pressure=0.0
            air=s.settings.setup.materials.fluid["air"]; air.density.option="ideal-gas"; air.viscosity.value=MU
            pin=s.settings.setup.boundary_conditions.pressure_inlet["inlet"]; pin.momentum.gauge_total_pressure.value=P0; pin.momentum.supersonic_or_initial_gauge_pressure.value=P0*0.8; pin.thermal.total_temperature.value=T0
            pout=s.settings.setup.boundary_conditions.pressure_outlet["outlet"]; pout.momentum.gauge_pressure.value=pexit; pout.thermal.backflow_total_temperature.value=T0
            s.settings.solution.initialization.hybrid_initialize(); s.settings.solution.run_calculation.iterate(iter_count=1400)
            quantities=["x-coordinate","y-coordinate","mach-number","pressure","temperature","density","x-velocity","velocity-magnitude"]
            raw=OUT/f"{CASE}_raw.csv"; s.settings.file.export.ascii(file_name=str(raw),surface_name_list=["interior","inlet","outlet"],delimiter="comma",quantities=quantities,location="node")
            s.settings.file.write_case_data(file_name=str(OUT/f"{CASE}.cas.h5"))
        rows=read_fluent_ascii_export(raw); center=[r for r in rows if abs(r["y-coordinate"])<1e-9]; center_by_x={}
        for r in center: center_by_x.setdefault(round(r["x-coordinate"],8),[]).append(r)
        axis=[]
        for x,vals in sorted(center_by_x.items()):
            axis.append({k:(x if k=="x-coordinate" else float(np.mean([v[k] for v in vals]))) for k in ("x-coordinate","mach-number","pressure","temperature","density")})
        throat=min(axis,key=lambda r:abs(r["x-coordinate"]-XT)); outlet=min(axis,key=lambda r:abs(r["x-coordinate"]-L))
        throat_profile=sorted([r for r in rows if abs(r["x-coordinate"]-XT)<1e-8],key=lambda r:r["y-coordinate"])
        mdot=float(np.trapezoid([r["density"]*r["x-velocity"] for r in throat_profile],[r["y-coordinate"] for r in throat_profile]))
        data_rows=[{"x_m":r["x-coordinate"],"mach":r["mach-number"],"pressure_pa":r["pressure"],"temperature_K":r["temperature"],"density_kg_m3":r["density"]} for r in axis]
        csv=write_csv(OUT/f"{CASE}_centerline.csv",list(data_rows[0]),data_rows)
        msvg=svg_xy_plot(OUT/f"{CASE}_mach_distribution.svg",[(r["x_m"],r["mach"]) for r in data_rows],title="Case F: nozzle centerline Mach number",xlabel="x (m)",ylabel="Mach")
        psvg=svg_field_map(OUT/f"{CASE}_pressure_field.svg",[(r["x-coordinate"],r["y-coordinate"],r["pressure"]) for r in rows],title="Case F: static pressure field")
        errors={"throat_mach":abs(throat["mach-number"]-1),"exit_mach_relative":rel_error(outlet["mach-number"],mex),"mass_flow_relative":rel_error(mdot,mdot_star),"throat_pressure_relative":rel_error(throat["pressure"],pstar)}
        checks={"throat_choked":.75<throat["mach-number"]<1.25,"exit_supersonic":outlet["mach-number"]>1.5,"exit_mach_error_lt_25pct":errors["exit_mach_relative"]<.25,"mass_flow_error_lt_25pct":errors["mass_flow_relative"]<.25,"temperature_drops":outlet["temperature"]<T0}
        payload.update({"results":{"mass_flow_per_depth_kg_m_s":mdot,"throat":throat,"outlet":outlet,"maximum_mach":max(r["mach-number"] for r in axis)},"isentropic_theory":{"critical_pressure_pa":pstar,"critical_pressure_ratio":pstar/P0,"critical_mass_flow_per_depth_kg_m_s":mdot_star,"exit_mach":mex,"exit_pressure_pa":pexit},"errors":errors,"checks":checks,"convergence":{"iterations_requested":1400},"status":"PASS" if all(checks.values()) else "FAIL","files":[str(p.resolve()) for p in (mesh,raw,csv,msvg,psvg,OUT/f"{CASE}.cas.h5")]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
