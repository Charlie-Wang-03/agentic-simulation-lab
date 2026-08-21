"""Case G: sequential thermal-to-structural free-expansion benchmark."""

from __future__ import annotations

import re

from thermal_smoke_common import *

CASE="thermal_structural"
L,W,H=0.10,0.01,0.01
K,E,NU,ALPHA=45.0,200e9,0.30,12e-6
TREF,THOT,ESIZE=20.0,80.0,0.01

def main()->int:
    clean_case(CASE)
    thermal_raw=OUT/f"{CASE}_temperature_raw.csv"; disp_raw=OUT/f"{CASE}_displacement_raw.csv"; summary=OUT/f"{CASE}_summary.csv"; profile=OUT/f"{CASE}_displacement.csv"; chart=OUT/f"{CASE}_expansion.svg"; result_file=OUT/f"{CASE}_results.json"
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
D,ALL,TEMP,{THOT}
ALLSEL,ALL
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
{apdl_export_nodes(thermal_raw)}
FINISH
/PREP7
DDELE,ALL,TEMP
ETCHG,TTS
MP,EX,1,{E}
MP,PRXY,1,{NU}
MP,ALPX,1,{ALPHA}
TREF,{TREF}
FINISH
/SOLU
ANTYPE,STATIC
LDREAD,TEMP,LAST,,,,{CASE},rth
NSEL,S,LOC,X,0
D,ALL,ALL,0
ALLSEL,ALL
SOLVE
FINISH
/POST1
SET,LAST
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
ALLSEL,ALL
*GET,NN,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_path(disp_raw.with_suffix(''))}','csv'
*DO,II,1,NN
  *GET,NX,NODE,NID,LOC,X
  *GET,UX,NODE,NID,U,X
  *VWRITE,NID,NX,UX
  (F12.0,',',E22.14,',',E22.14)
  NID=NDNEXT(NID)
*ENDDO
*CFCLOS
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NELEMS
(F12.0,',',F12.0)
*CFCLOS
/EXIT,NOSAVE
"""
    inp,solver_out=run_apdl(CASE,apdl)
    temps=numeric_rows(thermal_raw,["node_id","x_m","temperature_c"]); disps=numeric_rows(disp_raw,["node_id","x_m","ux_m"]); stats=scalar_row(summary,["node_count","element_count"])
    listing=solver_out.read_text(encoding="utf-8",errors="replace")
    mapped_match=re.search(r"TEMPERATURES AT\s+(\d+) SELECTED NODES WERE STORED",listing)
    mapped_nodes=int(mapped_match.group(1)) if mapped_match else 0
    buckets={}
    for r in disps: buckets.setdefault(round(r["x_m"],12),[]).append(r["ux_m"])
    curve=[{"x_m":x,"ux_m":sum(v)/len(v),"theory_ux_m":ALPHA*(THOT-TREF)*x} for x,v in sorted(buckets.items())]; write_csv(profile,curve)
    tip=max(r["ux_m"] for r in disps); theory_tip=ALPHA*(THOT-TREF)*L; avg_temp=sum(r["temperature_c"] for r in temps)/len(temps)
    errors={"tip_displacement_relative":rel_error(tip,theory_tip),"thermal_solution_temperature_absolute_c":abs(avg_temp-THOT)}
    checks={"thermal_field_is_uniform":max(r["temperature_c"] for r in temps)-min(r["temperature_c"] for r in temps)<1e-6,"ldread_mapped_all_nodes":mapped_nodes==int(stats["node_count"]),"thermal_solution_matches_applied_temperature":errors["thermal_solution_temperature_absolute_c"]<1e-6,"free_expansion_error_below_2pct":errors["tip_displacement_relative"]<0.02,"positive_expansion":tip>0}
    svg_plot(chart,[([r["x_m"] for r in curve],[r["ux_m"] for r in curve],"Ansys"),([r["x_m"] for r in curve],[r["theory_ux_m"] for r in curve],"alpha*dT*x")],"Case G: sequential thermal expansion","x [m]","Axial displacement [m]")
    files=[inp,solver_out,thermal_raw,disp_raw,profile,chart,result_file,OUT/f"{CASE}.rth",OUT/f"{CASE}.rst"]
    payload=result_payload("G","Sequential Steady Thermal -> Static Structural",{"length_m":L,"conductivity_w_mk":K,"youngs_modulus_pa":E,"poisson_ratio":NU,"thermal_expansion_1_k":ALPHA,"reference_temperature_c":TREF,"applied_temperature_c":THOT},{"nodes":int(stats["node_count"]),"elements":int(stats["element_count"])},{"thermal_solution_mean_temperature_c":avg_temp,"ldread_mapped_node_count":mapped_nodes,"tip_displacement_m":tip},{"tip_displacement_m":theory_tip,"formula":"alpha * delta_T * L"},errors,checks,files)
    write_json(result_file,payload); print(f"Case G {payload['status']}: tip={tip:.9g} m, theory={theory_tip:.9g} m")
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
