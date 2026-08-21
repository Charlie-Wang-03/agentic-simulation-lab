"""Case E: two solids joined by finite-conductance CONTA174/TARGE170 thermal contact."""

from __future__ import annotations

from thermal_smoke_common import *

CASE="thermal_contact"
L1,L2,W,H=0.05,0.05,0.02,0.02
K,HCONTACT,THOT,TCOLD,ESIZE=10.0,200.0,100.0,20.0,0.01

def component_export(path,component):
    return f"""CMSEL,S,{component}
*GET,NC,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_path(path.with_suffix(''))}','csv'
*DO,II,1,NC
  *GET,NT,NODE,NID,TEMP
  *VWRITE,NID,NT
  (F12.0,',',E22.14)
  NID=NDNEXT(NID)
*ENDDO
*CFCLOS
ALLSEL,ALL"""

def main()->int:
    clean_case(CASE)
    left_raw=OUT/f"{CASE}_left_interface.csv"; right_raw=OUT/f"{CASE}_right_interface.csv"; raw=OUT/f"{CASE}_raw.csv"; summary=OUT/f"{CASE}_summary.csv"
    ideal_raw=OUT/f"{CASE}_ideal_raw.csv"; ideal_summary=OUT/f"{CASE}_ideal_summary.csv"; chart=OUT/f"{CASE}_temperature.svg"; profile=OUT/f"{CASE}_profile.csv"; result_file=OUT/f"{CASE}_results.json"
    finite=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID70
ET,2,TARGE170
ET,3,CONTA174
KEYOPT,3,1,2
KEYOPT,3,12,5
R,2
RMODIF,2,14,{HCONTACT}
MP,KXX,1,{K}
BLOCK,0,{L1},0,{W},0,{H}
*GET,VLEFT,VOLU,0,NUM,MAX
BLOCK,{L1},{L1+L2},0,{W},0,{H}
*GET,VRIGHT,VOLU,0,NUM,MAX
ESIZE,{ESIZE}
MSHKEY,1
TYPE,1
MAT,1
VSEL,S,VOLU,,VLEFT
VMESH,ALL
ALLSEL,ALL
NSEL,S,LOC,X,{L1}
CM,LEFT_IF,NODE
ALLSEL,ALL
*GET,NMAX1,NODE,0,NUM,MAX
VSEL,S,VOLU,,VRIGHT
TYPE,1
MAT,1
VMESH,ALL
ALLSEL,ALL
NSEL,S,NODE,,NMAX1+1,99999999
NSEL,R,LOC,X,{L1}
CM,RIGHT_IF,NODE
ALLSEL,ALL
*GET,NSOLID,ELEM,0,COUNT
CMSEL,S,LEFT_IF
TYPE,2
REAL,2
ESLN,S,0
ESURF
ALLSEL,ALL
CMSEL,S,RIGHT_IF
TYPE,3
REAL,2
ESLN,S,0
ESURF
ALLSEL,ALL
NSEL,S,LOC,X,0
D,ALL,TEMP,{THOT}
NSEL,S,LOC,X,{L1+L2}
D,ALL,TEMP,{TCOLD}
ALLSEL,ALL
/SOLU
ANTYPE,STATIC
NROPT,FULL
NEQIT,80
NSUBST,10,100,1
SOLVE
FINISH
/POST1
SET,LAST
{apdl_sum_reaction(0.0)}
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
{component_export(left_raw,'LEFT_IF')}
{component_export(right_raw,'RIGHT_IF')}
{apdl_export_nodes(raw)}
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NSOLID,NELEMS,QREACTION
(F12.0,',',F12.0,',',F12.0,',',E22.14)
*CFCLOS
/EXIT,NOSAVE
"""
    ideal=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID70
MP,KXX,1,{K}
BLOCK,0,{L1+L2},0,{W},0,{H}
ESIZE,{ESIZE}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,TEMP,{THOT}
NSEL,S,LOC,X,{L1+L2}
D,ALL,TEMP,{TCOLD}
ALLSEL,ALL
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
{apdl_sum_reaction(0.0)}
{apdl_export_nodes(ideal_raw)}
*CFOPEN,'{apdl_path(ideal_summary.with_suffix(''))}','csv'
*VWRITE,QREACTION
(E22.14)
*CFCLOS
/EXIT,NOSAVE
"""
    inp,solver_out=run_apdl(CASE,finite); ideal_inp,ideal_out=run_apdl(CASE+"_ideal",ideal)
    left=numeric_rows(left_raw,["node_id","temperature_c"]); right=numeric_rows(right_raw,["node_id","temperature_c"]); nodes=numeric_rows(raw,["node_id","x_m","temperature_c"]); stats=scalar_row(summary,["node_count","solid_elements","all_elements","hot_reaction_w"]); ideal_nodes=numeric_rows(ideal_raw,["node_id","x_m","temperature_c"]); ideal_stats=scalar_row(ideal_summary,["hot_reaction_w"])
    tl=sum(r["temperature_c"] for r in left)/len(left); tr=sum(r["temperature_c"] for r in right)/len(right); jump=tl-tr; q=abs(stats["hot_reaction_w"]); qideal=abs(ideal_stats["hot_reaction_w"]); area=W*H
    rsolid=(L1+L2)/(K*area); rcontact=1/(HCONTACT*area); qtheory=(THOT-TCOLD)/(rsolid+rcontact); jumptheory=qtheory*rcontact; qidealtheory=(THOT-TCOLD)/rsolid
    finite_profile=[]
    for r in average_by_x(nodes):
        if abs(r["x_m"]-L1)<1e-12:
            finite_profile.extend([{"x_m":L1,"temperature_c":tl},{"x_m":L1,"temperature_c":tr}])
        else:
            finite_profile.append({"x_m":r["x_m"],"temperature_c":r["temperature_c"]})
    write_csv(profile,finite_profile)
    errors={"heat_flow_relative":rel_error(q,qtheory),"temperature_jump_relative":rel_error(jump,jumptheory),"ideal_heat_flow_relative":rel_error(qideal,qidealtheory)}
    checks={"contact_elements_created":stats["all_elements"]>stats["solid_elements"],"finite_heat_flow_error_below_2pct":errors["heat_flow_relative"]<0.02,"contact_jump_error_below_2pct":errors["temperature_jump_relative"]<0.02,"ideal_reference_error_below_1pct":errors["ideal_heat_flow_relative"]<0.01,"finite_contact_reduces_heat_flow":q<qideal,"finite_contact_creates_jump":jump>1.0}
    ideal_curve=average_by_x(ideal_nodes)
    svg_plot(chart,[([r["x_m"] for r in finite_profile],[r["temperature_c"] for r in finite_profile],"Finite TCC"),([r["x_m"] for r in ideal_curve],[r["temperature_c"] for r in ideal_curve],"Ideal contact")],"Case E: thermal contact resistance","x [m]","Temperature [C]")
    files=[inp,solver_out,ideal_inp,ideal_out,left_raw,right_raw,raw,ideal_raw,profile,chart,result_file]
    payload=result_payload("E","Steady-State Thermal with CONTA174/TARGE170",{"left_length_m":L1,"right_length_m":L2,"conductivity_w_mk":K,"thermal_contact_conductance_w_m2k":HCONTACT,"hot_temperature_c":THOT,"cold_temperature_c":TCOLD},{"nodes":int(stats["node_count"]),"solid_elements":int(stats["solid_elements"]),"contact_and_target_elements":int(stats["all_elements"]-stats["solid_elements"])},{"left_interface_temperature_c":tl,"right_interface_temperature_c":tr,"interface_jump_c":jump,"heat_flow_w":q,"ideal_contact_heat_flow_w":qideal},{"interface_jump_c":jumptheory,"heat_flow_w":qtheory,"contact_resistance_k_w":rcontact,"ideal_contact_heat_flow_w":qidealtheory},errors,checks,files)
    write_json(result_file,payload); print(f"Case E {payload['status']}: Q={q:.8g} W, jump={jump:.8g} C, ideal Q={qideal:.8g} W")
    return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
