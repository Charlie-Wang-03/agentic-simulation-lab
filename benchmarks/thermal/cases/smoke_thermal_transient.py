"""Case D: transient cooling of a small high-conductivity cube."""

from __future__ import annotations

import math

from thermal_smoke_common import *

CASE="thermal_transient"
SIDE=0.010
K,RHO,CP,HCONV=200.0,7800.0,500.0,15.0
T0,TINF,TEND,DT=100.0,20.0,1200.0,5.0

def main()->int:
    clean_case(CASE)
    raw=OUT/f"{CASE}_raw.csv"; history=OUT/f"{CASE}_history.csv"; summary=OUT/f"{CASE}_summary.csv"; chart=OUT/f"{CASE}_history.svg"; result_file=OUT/f"{CASE}_results.json"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID70
MP,KXX,1,{K}
MP,DENS,1,{RHO}
MP,C,1,{CP}
BLOCK,0,{SIDE},0,{SIDE},0,{SIDE}
ESIZE,{SIDE/2}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
ASEL,ALL
SFA,ALL,1,CONV,{HCONV},{TINF}
ALLSEL,ALL
NSEL,S,LOC,X,{SIDE/2}
NSEL,R,LOC,Y,{SIDE/2}
NSEL,R,LOC,Z,{SIDE/2}
*GET,NCENTER,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,{SIDE/2}
NSEL,R,LOC,Y,{SIDE/2}
NSEL,R,LOC,Z,0
*GET,NSURF,NODE,0,NUM,MIN
ALLSEL,ALL
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
/SOLU
ANTYPE,TRANS
TRNOPT,FULL
AUTOTS,OFF
KBC,1
TUNIF,{T0}
TIME,{DT}
DELTIM,{DT}
OUTRES,ALL,ALL
*CFOPEN,'{apdl_path(raw.with_suffix(''))}','csv'
*VWRITE,0,{T0},{T0}
(E22.14,',',E22.14,',',E22.14)
*DO,TT,{DT},{TEND},{DT}
  TIME,TT
  SOLVE
  *GET,TC,NODE,NCENTER,TEMP
  *GET,TS,NODE,NSURF,TEMP
  *VWRITE,TT,TC,TS
  (E22.14,',',E22.14,',',E22.14)
*ENDDO
*CFCLOS
FINISH
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NELEMS,NCENTER,NSURF
(F12.0,',',F12.0,',',F12.0,',',F12.0)
*CFCLOS
/EXIT,NOSAVE
"""
    inp,solver_out=run_apdl(CASE,apdl,timeout=300)
    rows=numeric_rows(raw,["time_s","center_temperature_c","surface_temperature_c"])
    volume=SIDE**3; area=6*SIDE**2; lc=volume/area; bi=HCONV*lc/K; tau=RHO*CP*volume/(HCONV*area)
    out=[]
    for r in rows:
        th=TINF+(T0-TINF)*math.exp(-r["time_s"]/tau)
        out.append({**r,"lumped_temperature_c":th})
    write_csv(history,out)
    stats=scalar_row(summary,["node_count","element_count","center_node","surface_node"])
    max_center_error=max(abs(r["center_temperature_c"]-r["lumped_temperature_c"]) for r in out)
    final=out[-1]; errors={"max_center_absolute_c":max_center_error,"final_center_absolute_c":abs(final["center_temperature_c"]-final["lumped_temperature_c"]),"center_surface_final_absolute_c":abs(final["center_temperature_c"]-final["surface_temperature_c"])}
    checks={"biot_below_0_1":bi<0.1,"history_has_241_points":len(out)==241,"temperature_monotonic":all(out[i+1]["center_temperature_c"]<=out[i]["center_temperature_c"] for i in range(len(out)-1)),"lumped_max_error_below_0_2c":max_center_error<0.2,"approaches_ambient":TINF<final["center_temperature_c"]<T0}
    svg_plot(chart,[([r["time_s"] for r in out],[r["center_temperature_c"] for r in out],"Ansys center"),([r["time_s"] for r in out],[r["surface_temperature_c"] for r in out],"Ansys surface"),([r["time_s"] for r in out],[r["lumped_temperature_c"] for r in out],"Lumped")],"Case D: transient convective cooling","Time [s]","Temperature [C]")
    files=[inp,solver_out,raw,history,chart,result_file]
    payload=result_payload("D","Transient Thermal",{"cube_side_m":SIDE,"conductivity_w_mk":K,"density_kg_m3":RHO,"specific_heat_j_kgk":CP,"convection_w_m2k":HCONV,"initial_temperature_c":T0,"ambient_temperature_c":TINF},{"nodes":int(stats["node_count"]),"elements":int(stats["element_count"])},{"final_center_temperature_c":final["center_temperature_c"],"final_surface_temperature_c":final["surface_temperature_c"],"time_constant_s":tau},{"final_lumped_temperature_c":final["lumped_temperature_c"],"time_constant_s":tau,"biot_number":bi},errors,checks,files)
    write_json(result_file,payload); print(f"Case D {payload['status']}: final center={final['center_temperature_c']:.8g} C, lumped={final['lumped_temperature_c']:.8g} C, Bi={bi:.3g}")
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
