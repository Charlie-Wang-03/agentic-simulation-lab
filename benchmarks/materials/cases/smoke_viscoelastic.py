"""Case C: Prony-series stress relaxation under a held axial strain."""

from __future__ import annotations

from solid_materials_common import *

CASE="viscoelastic"; E=10e6; NU=.30; GREL=.60; TAU=2.0; EPS=.01; L=.10; W=.02; H=.02; TEND=10.0


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"viscoelastic_raw.csv"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
MP,EX,1,{E}
MP,PRXY,1,{NU}
TB,PRONY,1,,1,SHEAR
TBDATA,1,{GREL},{TAU}
TB,PRONY,1,,1,BULK
TBDATA,1,{GREL},{TAU}
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
D,ALL,UX,{EPS*L}
ALLSEL
/SOLU
ANTYPE,TRANS
TRNOPT,FULL
NLGEOM,OFF
KBC,1
OUTRES,ALL,ALL
TIME,1E-5
NSUBST,1
SOLVE
TIME,{TEND}
DELTIM,.20,.02,.20
SOLVE
FINISH
/POST1
*GET,NSETS,ACTIVE,0,SET,NSET
*CFOPEN,'{ap(raw)}','csv'
SET,FIRST
*DO,II,1,NSETS
*GET,TT,ACTIVE,0,SET,TIME
NSEL,S,LOC,X,0
FSUM
*GET,RF,FSUM,0,ITEM,FX
ALLSEL
*VWRITE,TT,RF
(E22.14,',',E22.14)
*IF,II,LT,NSETS,THEN
SET,NEXT
*ENDIF
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl)
    got=numeric_rows(raw,["time_s","force_n"]); area=W*H
    rows=[]
    for r in got:
        t=max(0,r["time_s"]-1e-5); theory=E*EPS*((1-GREL)+GREL*__import__('math').exp(-t/TAU))
        rows.append({"time_s":t,"strain":EPS,"stress_pa":abs(r["force_n"])/area,"theory_stress_pa":theory,"relaxation_modulus_pa":abs(r["force_n"])/area/EPS})
    errs=[rel_error(r["stress_pa"],r["theory_stress_pa"]) for r in rows]
    checks={"history_has_40_points":len(rows)>=40,"stress_relaxes":rows[-1]["stress_pa"]<.55*rows[0]["stress_pa"],"long_term_modulus_positive":rows[-1]["relaxation_modulus_pa"]>0,"maximum_error_below_4pct":max(errs)<.04}
    data=payload("C","Prony stress-relaxation","Generalized Maxwell: TB,PRONY shear + bulk","Small-strain transient",{"element":"SOLID185","nominal_elements":10},{"E0_pa":E,"nu":NU,"relative_relaxing_modulus":GREL,"tau_s":TAU,"held_strain":EPS},
      {"samples":len(rows),"initial_stress_pa":rows[0]["stress_pa"],"final_stress_pa":rows[-1]["stress_pa"]},{"stress":"E0*eps*((1-g)+g*exp(-t/tau))"},{"maximum_relative_error":max(errs)},checks,[p["input"],p["solver"],p["log"],raw])
    return finish(CASE,data,rows,[([r["time_s"] for r in rows],[r["stress_pa"]/1e3 for r in rows],"MAPDL"),([r["time_s"] for r in rows],[r["theory_stress_pa"]/1e3 for r in rows],"Prony theory")],("Time [s]","Stress [kPa]"))


if __name__=="__main__": raise SystemExit(main())
