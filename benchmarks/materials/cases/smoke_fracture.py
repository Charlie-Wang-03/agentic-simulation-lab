"""Case F: mode-I center-crack quarter model with singular tip mesh and CINT SIFS."""

from __future__ import annotations

import math
from solid_materials_common import *

CASE="fracture"; E=210e9; NU=.30; SIGMA=10e6; A=.010; W=.050; H=.100; THICK=.001


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"fracture_raw.csv"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,PLANE183
KEYOPT,1,3,3
R,1,{THICK}
MP,EX,1,{E}
MP,PRXY,1,{NU}
K,1,0,0
K,2,{A},0
K,3,{W},0
K,4,{W},{H}
K,5,0,{H}
L,1,2
L,2,3
L,3,4
L,4,5
L,5,1
AL,1,2,3,4,5
KSCON,2,{A/20},1,8
ESIZE,{A/4}
MSHKEY,0
AMESH,ALL
NSEL,S,LOC,X,0
D,ALL,UX,0
NSEL,S,LOC,Y,0
NSEL,R,LOC,X,{A},{W}
D,ALL,UY,0
ALLSEL
LSEL,S,LINE,,4
NSLL,S,1
*GET,NTOP,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*DO,II,1,NTOP
F,NID,FY,{SIGMA*W*THICK}/NTOP
NID=NDNEXT(NID)
*ENDDO
ALLSEL
KSEL,S,KP,,2
NSLK,S
CM,CRACKTIP,NODE
ALLSEL
CINT,NEW,1
CINT,TYPE,SIFS,1
CINT,CTNC,CRACKTIP
CINT,NCON,5
CINT,SYMM,ON
CINT,NORM,0,2
/SOLU
ANTYPE,STATIC
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
SET,LAST
*GET,TIPNODE,NODE,0,NUM,MIN
CMSEL,S,CRACKTIP
*GET,TIPNODE,NODE,0,NUM,MIN
ALLSEL
*CFOPEN,'{ap(raw)}','csv'
*DO,IC,1,5
*GET,K1V,CINT,1,CTIP,TIPNODE,,IC,DTYPE,K1
*VWRITE,IC,K1V
(E22.14,',',E22.14)
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl); rows=numeric_rows(raw,["contour","ki_pa_sqrt_m"]); theory=SIGMA*math.sqrt(math.pi*A)
    stable=rows[1:]; kval=sum(r["ki_pa_sqrt_m"] for r in stable)/len(stable); scatter=(max(r["ki_pa_sqrt_m"] for r in stable)-min(r["ki_pa_sqrt_m"] for r in stable))/abs(kval)
    for r in rows: r["theory_ki_pa_sqrt_m"]=theory
    err=rel_error(kval,theory); checks={"five_contours":len(rows)==5,"ki_positive":kval>0,"contour_scatter_below_15pct":scatter<.15,"infinite_plate_error_below_12pct":err<.12}
    data=payload("F","Mode-I center crack SIF","Isotropic linear elastic fracture mechanics","Quarter-symmetry static fracture with CINT SIFS",{"element":"PLANE183 plane stress","crack_tip":"KSCON quarter-point singular elements","contours":5},{"half_crack_length_m":A,"half_width_m":W,"height_m":H,"remote_stress_pa":SIGMA,"thickness_m":THICK},
      {"mean_stable_ki_pa_sqrt_m":kval,"contour_values":rows,"contour_scatter_fraction":scatter},{"ki_pa_sqrt_m":theory,"formula":"K_I=sigma*sqrt(pi*a), wide-plate approximation"},{"relative_error":err},checks,[p["input"],p["solver"],p["log"],raw])
    return finish(CASE,data,rows,[([r["contour"] for r in rows],[r["ki_pa_sqrt_m"]/1e6 for r in rows],"MAPDL CINT"),([r["contour"] for r in rows],[theory/1e6 for r in rows],"infinite plate")],("Contour","K_I [MPa sqrt(m)]"))


if __name__=="__main__": raise SystemExit(main())
