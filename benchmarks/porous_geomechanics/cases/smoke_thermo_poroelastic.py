"""Case I: CPT212 structural-pore-pressure-thermal three-field benchmark."""

from __future__ import annotations

import csv
import math

from fluent_smoke_common import write_csv
from porous_geomechanics_common import *

CASE="thermo_poroelastic";H=1.;W=.1;E=100e6;NU=.25;K=1e-6;PHI=.3;RHO_S=2500.;RHO_W=1000.;G=9.81;KS=.8;CPS=800.;CPF=4180.;T0=293.15;TH=313.15;NY=20;TF=5000.;NSUB=100

def read_raw(path):
    rows=[]
    with path.open(encoding="utf-8",errors="replace") as f:
        for r in csv.reader(f):
            if len(r)<6:continue
            try:v=list(map(float,r[:6]));rows.append(dict(zip(("time_s","depth_m","temperature_K","pore_pressure_pa","uy_m","stress_y_pa"),v)))
            except ValueError:pass
    if not rows:raise RuntimeError(f"No thermo-poroelastic data in {path}")
    return rows

def main()->int:
    p=clean_case(CASE);raw=p["dir"] / "thermo_poroelastic_raw.csv";gamma_s=RHO_S*G;gamma_w=RHO_W*G
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,CPT212
KEYOPT,1,11,1
KEYOPT,1,12,1
KEYOPT,1,3,2
RECTNG,0,{W},-{H},0
LESIZE,4,,,{NY}
LESIZE,3,,,1
MSHKEY,1
AMESH,ALL
MP,EX,1,{E}
MP,NUXY,1,{NU}
TB,PM,1,,,PERM
TBDATA,1,{K},{K},{K}
TB,PM,1,,,BIOT
TBDATA,1,1.0
TB,PM,1,,,SP
TBDATA,1,{E/(3*(1-2*NU))},{gamma_s}
TB,PM,1,,,FP
TBDATA,1,2.2E9,{gamma_w},{PHI}
TB,THERM,1,,,COND
TBDATA,1,{KS}
TB,THERM,1,,,SPHT
TBDATA,1,{CPS}
TB,THERM,1,,,FLSPHT
TBDATA,1,{CPF}
TB,CTE,1
TBDATA,1,3.0E-5
TB,CTE,1,,,FLUID
TBDATA,1,2.0E-4
ALLSEL
D,ALL,UX,0
NSEL,S,LOC,Y,-{H}
D,ALL,UY,0
D,ALL,TEMP,{T0}
ALLSEL
NSEL,S,LOC,Y,0
D,ALL,PRES,0
D,ALL,TEMP,{TH}
ALLSEL
TUNIF,{T0}
FINISH
/SOLU
ANTYPE,SOIL
NROPT,UNSYM
TIME,{TF}
NSUBST,{NSUB},{NSUB},{NSUB}
KBC,1
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
*DO,II,1,{NSUB}
SET,1,II
*GET,TT,ACTIVE,0,SET,TIME
*DO,JJ,0,{NY}
DD={H}*JJ/{NY}
NN=NODE(0,-DD,0)
*GET,TN,NODE,NN,TEMP
*GET,PP,NODE,NN,PRES
*GET,UYV,NODE,NN,U,Y
*GET,SYV,NODE,NN,S,Y
*VWRITE,TT,DD,TN,PP,UYV,SYV
(E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
*ENDDO
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run=run_apdl(CASE,apdl,timeout=360)
    try:
        if run["exit_code"]!=0:raise RuntimeError("MAPDL nonzero exit; "+" ".join(line.strip() for line in run["listing"].splitlines() if "LICENSE" in line.upper())[:500])
        errs=[line.strip() for line in run["listing"].splitlines() if "*** ERROR ***" in line]
        if errs:raise RuntimeError(str(errs[:5]))
        rows=read_raw(raw);times=sorted({r["time_s"] for r in rows});first=[r for r in rows if r["time_s"]==times[0]];last=[r for r in rows if r["time_s"]==times[-1]];pmax=max(abs(r["pore_pressure_pa"]) for r in rows);umax=max(abs(r["uy_m"]) for r in rows);trange=max(r["temperature_K"] for r in last)-min(r["temperature_K"] for r in last);early_p=max(abs(r["pore_pressure_pa"]) for r in first);late_p=max(abs(r["pore_pressure_pa"]) for r in last)
        checks={"temperature_field_solved":trange>10,"pore_pressure_field_responds":pmax>1e-3,"displacement_field_responds":umax>1e-10,"drained_top_pressure_zero":abs(min(last,key=lambda r:r["depth_m"])["pore_pressure_pa"])<max(1e-3,pmax*.01),"all_fields_finite":all(math.isfinite(v) for r in rows for v in r.values())}
        csvp=write_csv(p["dir"] / "three_field_history.csv",list(rows[0]),rows)
        svg=p["dir"] / "three_field_ranges.svg"
        svg_plot(svg,[
            ([r["depth_m"] for r in last],[r["temperature_K"] for r in last],"temperature K"),
            ([r["depth_m"] for r in last],[r["pore_pressure_pa"]/max(pmax,1) for r in last],"normalized pore pressure"),
        ],"Case I: final three-field depth profiles","depth [m]","field value")
        payload=status_payload("I","Thermo-poroelastic three-field coupling","PASS" if all(checks.values()) else "FAIL",solver="Ansys MAPDL",analysis_type="ANTYPE,SOIL; CPT212 UX/UY/PRES/TEMP",material_model="saturated thermo-poroelastic medium",parameters={"E_pa":E,"nu":NU,"permeability_m_s":K,"porosity":PHI,"temperature_boundary_K":[T0,TH]},mesh={"element":"CPT212","elements":NY},time={"final_s":TF,"substeps":NSUB},results={"temperature_range_K":trange,"maximum_pore_pressure_pa":pmax,"maximum_displacement_m":umax,"early_max_pressure_pa":early_p,"late_max_pressure_pa":late_p},checks=checks,files=[str(x.resolve()) for x in (p["input"],p["solver"],p["log"],raw,csvp,svg)])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("I","Thermo-poroelastic three-field coupling",status,error=error,solver_output=str(p["solver"].resolve()))
    write_json(p["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT","BLOCKED BY STUDENT LIMIT","BLOCKED BY CURRENT API") else 1

if __name__=="__main__":raise SystemExit(main())
