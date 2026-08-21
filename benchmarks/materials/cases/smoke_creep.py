"""Case D: secondary Norton creep under constant axial stress."""

from __future__ import annotations

from solid_materials_common import *

CASE="creep"; E=200e9; NU=.30; SIGMA=100e6; C1=1e-30; N=3.0; L=.10; W=.02; H=.02; TEND=1000.0; TEMP=600.0


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"creep_raw.csv"; rate=C1*SIGMA**N
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
MP,EX,1,{E}
MP,PRXY,1,{NU}
TB,CREEP,1,,,6
TBDATA,1,{C1},{N},0,0
BLOCK,0,{L},0,{W},0,{H}
ESIZE,{W}
MSHKEY,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,UX,0
NSEL,S,LOC,Y,0
D,ALL,UY,0
NSEL,S,LOC,Z,0
D,ALL,UZ,0
NSEL,S,LOC,X,{L}
F,ALL,FX,{SIGMA*W*H/4}
ALLSEL
TUNIF,{TEMP}
/SOLU
ANTYPE,STATIC
NLGEOM,OFF
RATE,ON
KBC,1
OUTRES,ALL,ALL
TIME,1E-6
NSUBST,1
SOLVE
TIME,{TEND}
DELTIM,20,2,20
SOLVE
FINISH
/POST1
*GET,NSETS,ACTIVE,0,SET,NSET
*CFOPEN,'{ap(raw)}','csv'
SET,FIRST
*DO,II,1,NSETS
*GET,TT,ACTIVE,0,SET,TIME
NSEL,S,LOC,X,{L}
*GET,NN,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
US=0
*DO,JJ,1,NN
*GET,UU,NODE,NID,U,X
US=US+UU
NID=NDNEXT(NID)
*ENDDO
UA=US/NN
ALLSEL
ETABLE,CRX,EPCR,X
SSUM
*GET,CRSUM,SSUM,0,ITEM,CRX
*GET,NE,ELEM,0,COUNT
CR=CRSUM/NE
*VWRITE,TT,UA,CR
(E22.14,',',E22.14,',',E22.14)
*IF,II,LT,NSETS,THEN
SET,NEXT
*ENDIF
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl)
    got=numeric_rows(raw,["time_s","ux_m","creep_strain"]); rows=[]
    for r in got:
        t=max(0,r["time_s"]-1e-6); theory=rate*t
        rows.append({"time_s":t,"total_strain":r["ux_m"]/L,"creep_strain":r["creep_strain"],"theory_creep_strain":theory,"theory_total_strain":SIGMA/E+theory,"creep_rate_1_s":rate})
    late=rows[len(rows)//2:]; err=max(rel_error(r["creep_strain"],r["theory_creep_strain"]) for r in late)
    checks={"history_has_40_points":len(rows)>=40,"creep_grows":rows[-1]["creep_strain"]>rows[1]["creep_strain"],"positive_rate":rate>0,"late_time_error_below_5pct":err<.05}
    data=payload("D","Norton secondary creep","TB,CREEP,,,,6 (secondary creep)","Time-dependent static at elevated temperature",{"element":"SOLID185","nominal_elements":10},{"E_pa":E,"nu":NU,"stress_pa":SIGMA,"temperature_c":TEMP,"C1_pa_n_inv_s":C1,"stress_exponent":N},
      {"final_creep_strain":rows[-1]["creep_strain"],"creep_rate_1_s":rate},{"creep_strain":"C1*sigma^n*t"},{"late_time_max_relative_error":err},checks,[p["input"],p["solver"],p["log"],raw])
    return finish(CASE,data,rows,[([r["time_s"] for r in rows],[r["creep_strain"] for r in rows],"MAPDL"),([r["time_s"] for r in rows],[r["theory_creep_strain"] for r in rows],"Norton theory")],("Time [s]","Creep strain"))


if __name__=="__main__": raise SystemExit(main())
