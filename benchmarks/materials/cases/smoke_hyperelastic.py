"""Case B: large-deformation incompressible Neo-Hookean tension."""

from __future__ import annotations

from solid_materials_common import *

CASE="hyperelastic"; MU=1.0e6; L=.10; W=.02; H=.02; LAMBDAS=[1.0,1.1,1.2,1.3,1.4,1.5]


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"hyperelastic_raw.csv"
    solves=[]
    for i,lam in enumerate(LAMBDAS[1:],1):
        solves.append(f"TIME,{i}\nNSEL,S,LOC,X,{L}\nD,ALL,UX,{(lam-1)*L}\nALLSEL\nSOLVE")
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
KEYOPT,1,6,1
TB,HYPER,1,,,NEO
TBDATA,1,{MU}
BLOCK,0,{L},0,{W},0,{H}
ESIZE,{W/2}
MSHKEY,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,UX,0
NSEL,S,LOC,X,0
NSEL,R,LOC,Y,0
D,ALL,UY,0
NSEL,S,LOC,X,0
NSEL,R,LOC,Z,0
D,ALL,UZ,0
ALLSEL
/SOLU
ANTYPE,STATIC
NLGEOM,ON
NROPT,FULL
NSUBST,20,100,5
OUTRES,ALL,ALL
{chr(10).join(solves)}
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
*DO,II,1,{len(LAMBDAS)-1}
SET,II,LAST
*GET,TT,ACTIVE,0,SET,TIME
NSEL,S,LOC,X,0
FSUM
*GET,RF,FSUM,0,ITEM,FX
ALLSEL
*VWRITE,TT,RF
(E22.14,',',E22.14)
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl)
    got=numeric_rows(raw,["step","force_n"])
    rows=[{"stretch":1.0,"force_n":0.0,"nominal_stress_pa":0.0,"theory_nominal_stress_pa":0.0}]
    for r in got:
        lam=LAMBDAS[round(r["step"])]; theory=MU*(lam-lam**-2)
        rows.append({"stretch":lam,"force_n":r["force_n"],"nominal_stress_pa":r["force_n"]/(W*H),"theory_nominal_stress_pa":theory})
    errs=[rel_error(r["nominal_stress_pa"],r["theory_nominal_stress_pa"]) for r in rows[1:]]
    energy=sum(.5*(rows[i]["force_n"]+rows[i-1]["force_n"])*(rows[i]["stretch"]-rows[i-1]["stretch"])*L for i in range(1,len(rows)))
    theory_energy=(MU/2)*(1.5**2+2/1.5-3)*L*W*H
    checks={"stretch_at_least_1p5":rows[-1]["stretch"]>=1.5,"positive_force":rows[-1]["force_n"]>0,"stress_error_below_8pct":max(errs)<.08,"energy_error_below_10pct":rel_error(energy,theory_energy)<.10}
    data=payload("B","Neo-Hookean large-deformation tension","TB,HYPER,,,,NEO","Nonlinear static, NLGEOM=ON",{"element":"SOLID185 mixed u-P","nominal_elements":16},{"mu_pa":MU,"maximum_stretch":1.5},
      {"maximum_force_n":rows[-1]["force_n"],"strain_energy_j":energy},{"nominal_stress":"mu*(lambda-lambda^-2)","strain_energy_j":theory_energy},{"maximum_stress_relative_error":max(errs),"energy_relative_error":rel_error(energy,theory_energy)},checks,[p["input"],p["solver"],p["log"],raw])
    return finish(CASE,data,rows,[([r["stretch"] for r in rows],[r["nominal_stress_pa"]/1e6 for r in rows],"MAPDL"),([r["stretch"] for r in rows],[r["theory_nominal_stress_pa"]/1e6 for r in rows],"Neo-Hookean")],("Stretch ratio","Nominal stress [MPa]"))


if __name__=="__main__": raise SystemExit(main())
