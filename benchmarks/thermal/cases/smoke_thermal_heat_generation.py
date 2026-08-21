"""Case B: steady slab with uniform volumetric heat generation."""

from __future__ import annotations

from thermal_smoke_common import *

CASE="thermal_heat_generation"
L,W,H=0.10,0.02,0.02
K,QGEN,TWALL,ESIZE=12.0,2.4e5,25.0,0.01

def main()->int:
    clean_case(CASE)
    raw,summary=OUT/f"{CASE}_raw.csv",OUT/f"{CASE}_summary.csv"
    profile,chart,result_file=OUT/f"{CASE}_profile.csv",OUT/f"{CASE}_temperature.svg",OUT/f"{CASE}_results.json"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID70
MP,KXX,1,{K}
BLOCK,{-L/2},{L/2},0,{W},0,{H}
ESIZE,{ESIZE}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
BFE,ALL,HGEN,,{QGEN}
NSEL,S,LOC,X,{-L/2}
D,ALL,TEMP,{TWALL}
NSEL,S,LOC,X,{L/2}
D,ALL,TEMP,{TWALL}
ALLSEL,ALL
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
{apdl_sum_reaction(-L/2,'QLEFT')}
{apdl_sum_reaction(L/2,'QRIGHT')}
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
{apdl_export_nodes(raw)}
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NELEMS,QLEFT,QRIGHT
(F12.0,',',F12.0,',',E22.14,',',E22.14)
*CFCLOS
/EXIT,NOSAVE
"""
    inp,solver_out=run_apdl(CASE,apdl)
    nodes=numeric_rows(raw,["node_id","x_m","temperature_c"]); curve=average_by_x(nodes); write_csv(profile,curve)
    stats=scalar_row(summary,["node_count","element_count","left_reaction_w","right_reaction_w"])
    a=L/2
    theory=[{"x_m":r["x_m"],"temperature_c":TWALL+QGEN*(a*a-r["x_m"]**2)/(2*K)} for r in curve]
    tmax_theory=TWALL+QGEN*a*a/(2*K); tmax=max(r["temperature_c"] for r in nodes)
    generated=QGEN*L*W*H; removed=abs(stats["left_reaction_w"]+stats["right_reaction_w"])
    max_curve_error=max(abs(a1["temperature_c"]-b1["temperature_c"]) for a1,b1 in zip(curve,theory))
    errors={"center_temperature_relative_rise":rel_error(tmax-TWALL,tmax_theory-TWALL),"energy_balance_relative":rel_error(removed,generated),"max_profile_absolute_c":max_curve_error}
    checks={"center_is_hottest":abs(tmax-max(r["temperature_c"] for r in curve))<1e-6,"center_temperature_error_below_2pct":errors["center_temperature_relative_rise"]<0.02,"energy_balance_below_1pct":errors["energy_balance_relative"]<0.01,"profile_error_below_0_2c":max_curve_error<0.2}
    area=W*H
    flux_peak=max(abs(stats["left_reaction_w"]),abs(stats["right_reaction_w"]))/area
    svg_plot(chart,[([r["x_m"] for r in curve],[r["temperature_c"] for r in curve],"Ansys"),([r["x_m"] for r in theory],[r["temperature_c"] for r in theory],"Analytic")],"Case B: uniform internal heat generation","x [m]","Temperature [C]")
    files=[inp,solver_out,raw,profile,chart,result_file]
    payload=result_payload("B","Steady-State Thermal",{"length_m":L,"conductivity_w_mk":K,"heat_generation_w_m3":QGEN,"wall_temperature_c":TWALL},{"nodes":int(stats["node_count"]),"elements":int(stats["element_count"])},{"max_temperature_c":tmax,"removed_heat_w":removed,"peak_heat_flux_w_m2":flux_peak},{"max_temperature_c":tmax_theory,"generated_heat_w":generated,"peak_heat_flux_w_m2":QGEN*a},errors,checks,files)
    write_json(result_file,payload); print(f"Case B {payload['status']}: Tmax={tmax:.8g} C, theory={tmax_theory:.8g} C")
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
