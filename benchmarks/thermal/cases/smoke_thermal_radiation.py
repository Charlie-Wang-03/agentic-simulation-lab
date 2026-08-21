"""Case F: nonlinear radiation plus convection from a hot surface."""

from __future__ import annotations

import math

from thermal_smoke_common import *

CASE="thermal_radiation"
L,W,H=0.04,0.02,0.02
K,HCONV,EMISS,TINF,QIN,ESIZE=20.0,12.0,0.80,25.0,8000.0,0.01
SIGMA=5.670374419e-8

def equilibrium_temperature()->float:
    lo,hi=TINF,TINF+1000
    for _ in range(100):
        mid=(lo+hi)/2; tk=mid+273.15; ta=TINF+273.15
        loss=HCONV*(mid-TINF)+EMISS*SIGMA*(tk**4-ta**4)
        if loss<QIN: lo=mid
        else: hi=mid
    return (lo+hi)/2

def main()->int:
    clean_case(CASE)
    raw=OUT/f"{CASE}_raw.csv"; summary=OUT/f"{CASE}_summary.csv"; profile=OUT/f"{CASE}_profile.csv"; chart=OUT/f"{CASE}_temperature.svg"; result_file=OUT/f"{CASE}_results.json"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
TOFFST,273.15
STEF,{SIGMA}
ET,1,SOLID70
MP,KXX,1,{K}
BLOCK,0,{L},0,{W},0,{H}
ESIZE,{ESIZE}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
ASEL,S,LOC,X,0
SFA,ALL,1,HFLUX,{QIN}
ASEL,S,LOC,X,{L}
SFA,ALL,1,CONV,{HCONV},{TINF}
SFA,ALL,1,RDSF,{EMISS},1
ALLSEL,ALL
SPCTEMP,1,{TINF}
/SOLU
ANTYPE,STATIC
NROPT,FULL
NEQIT,80
CNVTOL,HEAT,,1e-6,2,1e-6
NSUBST,10,100,1
SOLVE
FINISH
/POST1
SET,LAST
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
{apdl_export_nodes(raw)}
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NELEMS
(F12.0,',',F12.0)
*CFCLOS
/EXIT,NOSAVE
"""
    inp,solver_out=run_apdl(CASE,apdl)
    nodes=numeric_rows(raw,["node_id","x_m","temperature_c"]); curve=average_by_x(nodes); write_csv(profile,curve); stats=scalar_row(summary,["node_count","element_count"])
    surface=[r["temperature_c"] for r in nodes if abs(r["x_m"]-L)<1e-10]; ts=sum(surface)/len(surface); ts_theory=equilibrium_temperature(); area=W*H
    qconv_flux=HCONV*(ts-TINF); qrad_flux=EMISS*SIGMA*((ts+273.15)**4-(TINF+273.15)**4); total=(qconv_flux+qrad_flux)*area; input_power=QIN*area
    errors={"surface_temperature_absolute_c":abs(ts-ts_theory),"energy_balance_relative":rel_error(total,input_power)}
    checks={"surface_temperature_error_below_0_2c":errors["surface_temperature_absolute_c"]<0.2,"energy_balance_below_1pct":errors["energy_balance_relative"]<0.01,"radiation_is_nonzero":qrad_flux>0,"convection_is_nonzero":qconv_flux>0}
    svg_plot(chart,[([r["x_m"] for r in curve],[r["temperature_c"] for r in curve],"Ansys")],"Case F: nonlinear radiation boundary","x [m]","Temperature [C]")
    files=[inp,solver_out,raw,profile,chart,result_file]
    payload=result_payload("F","Steady-State Thermal (nonlinear radiation)",{"length_m":L,"conductivity_w_mk":K,"input_heat_flux_w_m2":QIN,"emissivity":EMISS,"convection_w_m2k":HCONV,"ambient_temperature_c":TINF},{"nodes":int(stats["node_count"]),"elements":int(stats["element_count"])},{"equilibrium_surface_temperature_c":ts,"radiation_heat_flux_w_m2":qrad_flux,"convection_heat_flux_w_m2":qconv_flux,"radiation_power_w":qrad_flux*area,"convection_power_w":qconv_flux*area,"total_dissipation_w":total},{"equilibrium_surface_temperature_c":ts_theory,"input_power_w":input_power},errors,checks,files)
    write_json(result_file,payload); print(f"Case F {payload['status']}: Ts={ts:.8g} C, theory={ts_theory:.8g} C, radiation={qrad_flux*area:.8g} W, convection={qconv_flux*area:.8g} W")
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
