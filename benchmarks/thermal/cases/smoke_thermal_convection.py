"""Case C: conduction through a wall terminated by a convection boundary."""

from __future__ import annotations

from thermal_smoke_common import *

CASE="thermal_convection"
L,W,H=0.08,0.025,0.020
K,HCONV,THOT,TINF,ESIZE=8.0,40.0,100.0,20.0,0.01

def main()->int:
    clean_case(CASE)
    raw,summary=OUT/f"{CASE}_raw.csv",OUT/f"{CASE}_summary.csv"; profile=OUT/f"{CASE}_profile.csv"; chart=OUT/f"{CASE}_temperature.svg"; result_file=OUT/f"{CASE}_results.json"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID70
MP,KXX,1,{K}
BLOCK,0,{L},0,{W},0,{H}
ESIZE,{ESIZE}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,TEMP,{THOT}
NSEL,S,LOC,X,{L}
SF,ALL,CONV,{HCONV},{TINF}
ALLSEL,ALL
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
{apdl_sum_reaction(0.0)}
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
{apdl_export_nodes(raw)}
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NELEMS,QREACTION
(F12.0,',',F12.0,',',E22.14)
*CFCLOS
/EXIT,NOSAVE
"""
    inp,solver_out=run_apdl(CASE,apdl); nodes=numeric_rows(raw,["node_id","x_m","temperature_c"]); curve=average_by_x(nodes); write_csv(profile,curve); stats=scalar_row(summary,["node_count","element_count","hot_reaction_w"])
    area=W*H; rcond=L/(K*area); rconv=1/(HCONV*area); q_theory=(THOT-TINF)/(rcond+rconv); ts_theory=TINF+q_theory*rconv
    q=abs(stats["hot_reaction_w"]); surface_rows=[r for r in nodes if abs(r["x_m"]-L)<1e-10]; ts=sum(r["temperature_c"] for r in surface_rows)/len(surface_rows)
    gradient=(ts-THOT)/L
    errors={"heat_flow_relative":rel_error(q,q_theory),"surface_temperature_absolute_c":abs(ts-ts_theory),"energy_balance_relative":rel_error(HCONV*area*(ts-TINF),q)}
    checks={"heat_flow_error_below_1pct":errors["heat_flow_relative"]<0.01,"surface_temperature_error_below_0_1c":errors["surface_temperature_absolute_c"]<0.1,"convection_energy_balance_below_1pct":errors["energy_balance_relative"]<0.01}
    theory=[{"x_m":r["x_m"],"temperature_c":THOT+(ts_theory-THOT)*r["x_m"]/L} for r in curve]
    svg_plot(chart,[([r["x_m"] for r in curve],[r["temperature_c"] for r in curve],"Ansys"),([r["x_m"] for r in theory],[r["temperature_c"] for r in theory],"R-network")],"Case C: conduction plus convection","x [m]","Temperature [C]")
    files=[inp,solver_out,raw,profile,chart,result_file]
    payload=result_payload("C","Steady-State Thermal",{"length_m":L,"conductivity_w_mk":K,"convection_w_m2k":HCONV,"hot_temperature_c":THOT,"ambient_temperature_c":TINF},{"nodes":int(stats["node_count"]),"elements":int(stats["element_count"])},{"surface_temperature_c":ts,"temperature_gradient_c_m":gradient,"convection_power_w":HCONV*area*(ts-TINF),"heat_flow_w":q},{"surface_temperature_c":ts_theory,"heat_flow_w":q_theory,"conduction_resistance_k_w":rcond,"convection_resistance_k_w":rconv},errors,checks,files)
    write_json(result_file,payload); print(f"Case C {payload['status']}: Ts={ts:.8g} C, Q={q:.8g} W")
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
