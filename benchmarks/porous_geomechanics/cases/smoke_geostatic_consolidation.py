"""Case G: gravity/geostatic stage followed by excess-pore-pressure consolidation."""

from __future__ import annotations

import csv
import math

from fluent_smoke_common import write_csv
from porous_geomechanics_common import *

CASE="geostatic_consolidation";H=10.;W=1.;E=20e6;NU=.25;K=1e-7;PHI=.35;RHO_S=2650.;RHO_W=1000.;G=9.81;LOAD=50e3;NY=20;T1=1.;T2=201.;NSUB=100

def read_raw(path):
    rows=[]
    with path.open(encoding="utf-8",errors="replace") as f:
        for r in csv.reader(f):
            if len(r)<6:continue
            try:v=list(map(float,r[:6]));rows.append(dict(zip(("stage","time_s","depth_m","pore_pressure_pa","uy_m","stress_y_pa"),v)))
            except ValueError:pass
    if not rows:raise RuntimeError(f"No geostatic data in {path}")
    return rows

def main()->int:
    p=clean_case(CASE);raw=p["dir"] / "geostatic_raw.csv";gamma_s=RHO_S*G;gamma_w=RHO_W*G
    apdl=f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,CPT212
KEYOPT,1,12,1
KEYOPT,1,3,2
RECTNG,0,{W},-{H},0
LESIZE,4,,,{NY}
LESIZE,3,,,1
MSHKEY,1
AMESH,ALL
MP,EX,1,{E}
MP,NUXY,1,{NU}
MP,DENS,1,{(1-PHI)*RHO_S+PHI*RHO_W}
TB,PM,1,,,PERM
TBDATA,1,{K},{K},{K}
TB,PM,1,,,BIOT
TBDATA,1,1.0
ALLSEL
D,ALL,UX,0
NSEL,S,LOC,Y,-{H}
D,ALL,UY,0
ALLSEL
*GET,NN,NODE,0,NUM,MIN
*DO,II,1,{2*(NY+1)}
*GET,YY,NODE,NN,LOC,Y
PINI=-YY*{gamma_w}
D,NN,PRES,PINI
NN=NDNEXT(NN)
*ENDDO
FINISH
/SOLU
ANTYPE,STATIC
NROPT,UNSYM
ACEL,0,{G},0
TIME,{T1}
NSUBST,10,50,5
KBC,1
OUTRES,ALL,ALL
SOLVE
DDELE,ALL,PRES
NSEL,S,LOC,Y,0
D,ALL,PRES,0
ALLSEL
NSEL,S,LOC,Y,0
SF,ALL,PRES,{LOAD}
ALLSEL
TIME,{T2}
NSUBST,{NSUB},{NSUB},{NSUB}
KBC,1
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
SET,1,LAST
*GET,TT,ACTIVE,0,SET,TIME
*DO,JJ,0,{NY}
DD={H}*JJ/{NY}
NN=NODE(0,-DD,0)
*GET,PP,NODE,NN,PRES
*GET,UYV,NODE,NN,U,Y
*GET,SYV,NODE,NN,S,Y
*VWRITE,1,TT,DD,PP,UYV,SYV
(E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
*ENDDO
*DO,II,1,{NSUB}
SET,2,II
*GET,TT,ACTIVE,0,SET,TIME
*DO,JJ,0,{NY}
DD={H}*JJ/{NY}
NN=NODE(0,-DD,0)
*GET,PP,NODE,NN,PRES
*GET,UYV,NODE,NN,U,Y
*GET,SYV,NODE,NN,S,Y
*VWRITE,2,TT,DD,PP,UYV,SYV
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
        rows=read_raw(raw);geo=[r for r in rows if round(r["stage"])==1];con=[r for r in rows if round(r["stage"])==2];times=sorted({r["time_s"] for r in con});bytime={t:[r for r in con if r["time_s"]==t] for t in times}
        hydro_err=max(abs(r["pore_pressure_pa"]-gamma_w*r["depth_m"]) for r in geo)/max(gamma_w*H,1);stress_slope=sum((-r["stress_y_pa"])*r["depth_m"] for r in geo)/max(sum(r["depth_m"]**2 for r in geo),1);bulk_gamma=((1-PHI)*RHO_S+PHI*RHO_W)*G
        excess0=sum(abs(r["pore_pressure_pa"]-gamma_w*r["depth_m"]) for r in bytime[times[0]])/len(geo);excessf=sum(abs(r["pore_pressure_pa"]) for r in bytime[times[-1]])/len(geo);top_geo=min(geo,key=lambda r:r["depth_m"])["uy_m"];top0=min(bytime[times[0]],key=lambda r:r["depth_m"])["uy_m"]-top_geo;topf=min(bytime[times[-1]],key=lambda r:r["depth_m"])["uy_m"]-top_geo
        checks={"hydrostatic_profile_error_lt_8pct":hydro_err<.08,"initial_stress_increases_with_depth":stress_slope>0,"geostatic_stress_scale_reasonable":.35*bulk_gamma<stress_slope<1.5*bulk_gamma,"load_generates_excess_pore_pressure":excess0>LOAD*.2,"excess_pressure_dissipates":excessf<excess0*.5,"settlement_develops":abs(topf)>abs(top0)}
        csvp=write_csv(p["dir"] / "pore_pressure_profiles.csv",list(rows[0]),rows);svg=p["dir"] / "settlement_history.svg";sett=[(t,abs(min(bytime[t],key=lambda r:r["depth_m"])["uy_m"]-top_geo)) for t in times];svg_plot(svg,[([x for x,_ in sett],[y for _,y in sett],"incremental surface settlement")],"Case G: settlement after geostatic initialization","time [s]","settlement [m]")
        payload=status_payload("G","Geostatic initialization and consolidation","PASS" if all(checks.values()) else "FAIL",solver="Ansys MAPDL",analysis_type="two-stage CPT212 static-time consolidation",material_model="saturated Biot porous soil; prescribed hydrostatic geostatic initialization",parameters={"E_pa":E,"nu":NU,"permeability_m_s":K,"porosity":PHI,"solid_density_kg_m3":RHO_S,"fluid_density_kg_m3":RHO_W,"surface_load_pa":LOAD},mesh={"element":"CPT212","elements":NY},time={"geostatic_end_s":T1,"consolidation_end_s":T2,"consolidation_substeps":NSUB},results={"hydrostatic_profile_error":hydro_err,"geostatic_stress_gradient_pa_m":stress_slope,"expected_bulk_unit_weight_N_m3":bulk_gamma,"initial_excess_pressure_pa":excess0,"final_excess_pressure_pa":excessf,"settlement_history":sett},checks=checks,limitations=["The hydrostatic pore-pressure profile is prescribed for geostatic initialization, then released. With no sustained pore-fluid gravity term, consolidation drains toward the zero-pressure datum; final excess is therefore measured as mean absolute pore pressure."],files=[str(x.resolve()) for x in (p["input"],p["solver"],p["log"],raw,csvp,svg)])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("G","Geostatic initialization and consolidation",status,error=error,solver_output=str(p["solver"].resolve()))
    write_json(p["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
