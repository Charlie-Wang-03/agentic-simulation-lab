"""Case H: plane-strain compression with native Mohr-Coulomb plasticity."""

from __future__ import annotations

import csv
import math

from fluent_smoke_common import write_csv
from porous_geomechanics_common import *

CASE="geomechanics_material";E=10e6;NU=.3;C=20e3;PHI=30.;PSI=5.;L=.1;PCONF=50e3;MAX_STRAIN=.05;NSUB=100

def read_raw(path):
    rows=[]
    with path.open(encoding="utf-8",errors="replace") as f:
        for r in csv.reader(f):
            if len(r)<6:continue
            try:v=list(map(float,r[:6]));rows.append(dict(zip(("time","axial_strain","axial_stress_pa","volumetric_strain","equivalent_plastic_strain","reaction_n"),v)))
            except ValueError:pass
    if not rows:raise RuntimeError(f"No triaxial data in {path}")
    return rows

def main()->int:
    p=clean_case(CASE);raw=p["dir"] / "triaxial_raw.csv"
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,PLANE182
KEYOPT,1,1,3
KEYOPT,1,3,2
MP,EX,1,{E}
MP,PRXY,1,{NU}
TB,MC,1,,,BASE
TBDATA,1,{PHI},{C},{PSI},{PHI},{C}
RECTNG,0,{L},0,{L}
ESIZE,{L/10}
MSHKEY,1
AMESH,ALL
NSEL,S,LOC,X,0
D,ALL,UX,0
NSEL,S,LOC,Y,0
D,ALL,UY,0
ALLSEL
FINISH
/SOLU
ANTYPE,STATIC
NLGEOM,OFF
NROPT,UNSYM
KBC,0
LSEL,S,LOC,X,{L}
SFL,ALL,PRES,{PCONF}
ALLSEL
TIME,1
NSUBST,20,100,10
OUTRES,ALL,ALL
SOLVE
NSEL,S,LOC,Y,{L}
D,ALL,UY,-{MAX_STRAIN*L}
ALLSEL
TIME,2
NSUBST,{NSUB},{NSUB},{NSUB}
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
*DO,II,1,{NSUB}
SET,2,II
*GET,TT,ACTIVE,0,SET,TIME
NSEL,S,LOC,Y,{L}
*GET,NTOP,NODE,0,NUM,MIN
*GET,UYM,NODE,NTOP,U,Y
FSUM
*GET,RF,FSUM,0,ITEM,FY
ALLSEL
NSEL,S,LOC,X,{L}
*GET,NSIDE,NODE,0,NUM,MIN
*GET,UXM,NODE,NSIDE,U,X
ALLSEL
ETABLE,EPEQ,EPPL,EQV
SSUM
*GET,EPSUM,SSUM,0,ITEM,EPEQ
*GET,NE,ELEM,0,COUNT
EPAVG=EPSUM/NE
EZA=-UYM/{L}
SZA=ABS(RF)/{L}
EVOL=UXM/{L}+UYM/{L}
*VWRITE,TT,EZA,SZA,EVOL,EPAVG,RF
(E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run=run_apdl(CASE,apdl,timeout=300)
    try:
        if run["exit_code"]!=0:raise RuntimeError("MAPDL nonzero exit; "+" ".join(line.strip() for line in run["listing"].splitlines() if "LICENSE" in line.upper())[:500])
        errs=[line.strip() for line in run["listing"].splitlines() if "*** ERROR ***" in line]
        if errs:raise RuntimeError(str(errs[:5]))
        rows=read_raw(raw);sin=math.sin(math.radians(PHI));theory=PCONF*(1+sin)/(1-sin)+2*C*math.cos(math.radians(PHI))/(1-sin)
        yielded=[r for r in rows if r["equivalent_plastic_strain"]>1e-5];measured=yielded[0]["axial_stress_pa"] if yielded else float("inf");plateau=max(r["axial_stress_pa"] for r in rows);err=relative_error(measured,theory)
        checks={"confining_pressure_positive":PCONF>0,"yield_reached":bool(yielded),"yield_error_lt_18pct":err<.18,"plastic_strain_grows":rows[-1]["equivalent_plastic_strain"]>max(1e-4,rows[0]["equivalent_plastic_strain"]),"finite_volumetric_strain":all(math.isfinite(r["volumetric_strain"]) for r in rows)}
        csvp=write_csv(p["dir"] / "axial_stress_strain.csv",list(rows[0]),rows);svg=p["dir"] / "axial_stress_strain.svg";svg_plot(svg,[([r["axial_strain"] for r in rows],[r["axial_stress_pa"]/1e3 for r in rows],"MAPDL Mohr-Coulomb"),([0,max(r["axial_strain"] for r in rows)],[theory/1e3,theory/1e3],"MC meridian theory")],"Case H: confined Mohr-Coulomb compression","axial strain","axial stress [kPa]")
        payload=status_payload("H","Nonlinear geomechanical plane-strain compression","PASS" if all(checks.values()) else "FAIL",solver="Ansys MAPDL",analysis_type="nonlinear plane-strain compression",material_model="Mohr-Coulomb TB,MC",parameters={"E_pa":E,"nu":NU,"cohesion_pa":C,"friction_angle_deg":PHI,"dilation_angle_deg":PSI,"confining_pressure_pa":PCONF},mesh={"element":"PLANE182","nominal_elements":100},results={"measured_yield_axial_stress_pa":measured,"maximum_axial_stress_pa":plateau,"maximum_plastic_strain":max(r["equivalent_plastic_strain"] for r in rows),"final_volumetric_strain":rows[-1]["volumetric_strain"]},theory={"mohr_coulomb_compression_meridian_pa":theory,"formula":"sigma1=sigma3(1+sin(phi))/(1-sin(phi))+2c cos(phi)/(1-sin(phi))"},errors={"yield_relative":err},checks=checks,limitations=["Plane-strain confinement adds an out-of-plane stress, so the triaxial compression-meridian comparison uses an 18% engineering tolerance."],files=[str(x.resolve()) for x in (p["input"],p["solver"],p["log"],raw,csvp,svg)])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("H","Nonlinear geomechanical plane-strain compression",status,error=error,solver_output=str(p["solver"].resolve()))
    write_json(p["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
