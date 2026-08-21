"""Case E: elastic cyclic stress solution plus S-N/Goodman fatigue assessment."""

from __future__ import annotations

import math
from solid_materials_common import *

CASE="fatigue"; E=210e9; NU=.30; SUT=600e6; SMAX=240e6; SMIN=40e6; L=.10; W=.01; H=.01
SN=[(1e3,420e6),(1e4,330e6),(1e5,260e6),(1e6,205e6),(1e7,170e6)]


def sn_life(stress:float)->float:
    for (n1,s1),(n2,s2) in zip(SN,SN[1:]):
        if s2 <= stress <= s1:
            x=math.log10(n1)+(math.log10(stress)-math.log10(s1))*(math.log10(n2)-math.log10(n1))/(math.log10(s2)-math.log10(s1))
            return 10**x
    return SN[0][0] if stress>SN[0][1] else SN[-1][0]


def main()->int:
    p=clean_case(CASE); raw=p["dir"]/"fatigue_raw.csv"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID185
MP,EX,1,{E}
MP,PRXY,1,{NU}
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
ALLSEL
/SOLU
ANTYPE,STATIC
OUTRES,ALL,ALL
NSEL,S,LOC,X,{L}
F,ALL,FX,{SMAX*W*H/4}
ALLSEL
TIME,1
SOLVE
NSEL,S,LOC,X,{L}
FDELE,ALL,FX
F,ALL,FX,{SMIN*W*H/4}
ALLSEL
TIME,2
SOLVE
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
*DO,II,1,2
SET,II,LAST
NSEL,S,LOC,X,0
FSUM
*GET,RF,FSUM,0,ITEM,FX
ALLSEL
ETABLE,SEQV,S,EQV
SSUM
*GET,SS,SSUM,0,ITEM,SEQV
*GET,NE,ELEM,0,COUNT
SA=SS/NE
*VWRITE,II,RF,SA
(E22.14,',',E22.14,',',E22.14)
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run_apdl(CASE,apdl); got=numeric_rows(raw,["step","reaction_n","equivalent_stress_pa"])
    smax,smin=got[0]["equivalent_stress_pa"],got[1]["equivalent_stress_pa"]
    sa=(smax-smin)/2; sm=(smax+smin)/2; corrected=sa/(1-sm/SUT); life=sn_life(corrected); damage=1/life
    allowable=next(s for n,s in SN if n==1e6)*(1-sm/SUT); sf=allowable/sa
    rows=[{"cycles":n,"sn_stress_amplitude_pa":s,"goodman_allowable_at_mean_pa":s*(1-sm/SUT)} for n,s in SN]
    checks={"two_stress_states_solved":len(got)==2,"stress_range_positive":sa>0,"reaction_load_conserved":max(abs(abs(r["reaction_n"])-x*W*H)/(x*W*H) for r,x in zip(got,[SMAX,SMIN]))<.01,"life_within_sn_range":1e3<=life<=1e7,"finite_damage":math.isfinite(damage) and damage>0}
    data=payload("E","S-N fatigue with Goodman mean-stress correction","Linear elasticity + project-side S-N curve","Two static extrema; stress-life postprocessing",{"element":"SOLID185","nominal_elements":10},{"maximum_stress_pa":SMAX,"minimum_stress_pa":SMIN,"ultimate_strength_pa":SUT,"sn_curve":SN},
      {"alternating_stress_pa":sa,"mean_stress_pa":sm,"goodman_corrected_amplitude_pa":corrected,"life_cycles":life,"damage_per_cycle":damage,"safety_factor_at_1e6_cycles":sf},
      {"goodman":"sigma_a_corrected=sigma_a/(1-sigma_m/Sut)","sn_interpolation":"piecewise log-log"},{"reaction_balance_max_fraction":max(abs(abs(r["reaction_n"])-x*W*H)/(x*W*H) for r,x in zip(got,[SMAX,SMIN]))},checks,[p["input"],p["solver"],p["log"],raw],
      ["MAPDL supplies the resolved cyclic stress extrema; fatigue life is evaluated by the project-side documented S-N/Goodman postprocessor, not the Mechanical Fatigue Tool."])
    return finish(CASE,data,rows,[([math.log10(r["cycles"]) for r in rows],[r["sn_stress_amplitude_pa"]/1e6 for r in rows],"zero mean S-N"),([math.log10(r["cycles"]) for r in rows],[r["goodman_allowable_at_mean_pa"]/1e6 for r in rows],"Goodman at solved mean")],("log10(cycles)","Stress amplitude [MPa]"))


if __name__=="__main__": raise SystemExit(main())
