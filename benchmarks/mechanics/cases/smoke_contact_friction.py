"""MAPDL nonlinear transient smoke test for Coulomb sliding contact."""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

from dynamics_smoke_common import OUT, apdl_path, read_numeric_csv, run_mapdl, svg_plot, write_csv, write_json


MU = 0.20
GRAVITY = 9.80665
INITIAL_VELOCITY = 1.0
END_TIME = 0.30
TIME_STEP = 0.002
WIDTH = 0.10
HEIGHT = 0.05
THICKNESS = 0.02
DENSITY = 1000.0
YOUNGS_MODULUS = 2.0e9

INPUT=OUT/"contact_friction.inp"
SOLVER_OUT=OUT/"contact_friction_solver.out"
RAW=OUT/"contact_friction_raw.csv"
HISTORY=OUT/"contact_friction_history.csv"
RESULT=OUT/"contact_friction_results.json"
PLOT=OUT/"contact_friction_response.svg"


def apdl() -> str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,PLANE182
KEYOPT,1,3,3
R,1,{THICKNESS}
MP,EX,1,{YOUNGS_MODULUS}
MP,PRXY,1,0.3
MP,DENS,1,{DENSITY}
MP,MU,1,{MU}
BLC4,0,0,{WIDTH},{HEIGHT}
TYPE,1
REAL,1
MAT,1
ESIZE,0.01
AMESH,ALL
NSEL,S,LOC,X,{WIDTH/2}
NSEL,R,LOC,Y,{HEIGHT}
*GET,TRACK,NODE,0,NUM,MIN
ALLSEL,ALL
ET,2,TARGE169
ET,3,CONTA172
KEYOPT,3,2,0
KEYOPT,3,10,2
R,2
N,1001,-1,0,0
N,1002,1,0,0
TYPE,2
REAL,2
E,1002,1001
D,1001,ALL,0
D,1002,ALL,0
NSEL,S,LOC,Y,0
NSEL,R,LOC,X,0,{WIDTH}
TYPE,3
REAL,2
MAT,1
ESURF
ALLSEL,ALL
ESEL,S,TYPE,,1
NSLE,S
IC,ALL,UX,0,{INITIAL_VELOCITY}
ALLSEL,ALL
FINISH
/SOLU
ANTYPE,TRANS
TRNOPT,FULL
NLGEOM,ON
NROPT,FULL
KBC,1
AUTOTS,ON
DELTIM,{TIME_STEP},{TIME_STEP/4},{TIME_STEP}
OUTRES,ALL,ALL
ACEL,0,{GRAVITY},0
TIME,{END_TIME}
SOLVE
FINISH
/POST1
*GET,NSETS,ACTIVE,0,SET,NSET
*DIM,CSTATV,ARRAY,1000
*DIM,CPRESV,ARRAY,1000
*DIM,CFRICV,ARRAY,1000
*CFOPEN,'{apdl_path(RAW.with_suffix(''))}','csv'
*DO,II,1,NSETS
SET,1,II
*GET,TT,ACTIVE,0,SET,TIME
*GET,UX,NODE,TRACK,U,X
*GET,VX,NODE,TRACK,V,X
*GET,AX,NODE,TRACK,A,X
*GET,AY,NODE,TRACK,A,Y
ESEL,S,TYPE,,3
ETABLE,CSTAT,CONT,STAT
ETABLE,CPRES,CONT,PRES
ETABLE,CFRIC,CONT,STOT
*VGET,CSTATV(1),ELEM,1,ETAB,CSTAT
*VGET,CPRESV(1),ELEM,1,ETAB,CPRES
*VGET,CFRICV(1),ELEM,1,ETAB,CFRIC
*VSCFUN,STATMAX,MAX,CSTATV(1)
*VSCFUN,PMAX,MAX,CPRESV(1)
*VSCFUN,FMAX,MAX,CFRICV(1)
NSEL,S,NODE,,1001,1002
FSUM,,BOTH
*GET,RX,FSUM,0,ITEM,FX
*GET,RY,FSUM,0,ITEM,FY
*VWRITE,TT,UX,VX,AX,AY,STATMAX,PMAX,FMAX,RX,RY
(E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12)
ALLSEL,ALL
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for p in (INPUT,SOLVER_OUT,RAW,HISTORY,RESULT,PLOT):p.unlink(missing_ok=True)
    INPUT.write_text(apdl(),encoding="ascii")
    if run_mapdl("contact_friction",INPUT,SOLVER_OUT,timeout=240):return 1
    columns=["time_s","displacement_x_m","velocity_x_m_s","acceleration_x_m_s2","acceleration_y_m_s2","contact_status","max_contact_pressure_pa","max_total_contact_stress_pa","ground_reaction_x_n","ground_reaction_y_n"]
    rows=read_numeric_csv(RAW,columns)
    if len(rows)<50:raise RuntimeError(f"Expected contact history, got {len(rows)}")
    theoretical_velocity=max(0.0,INITIAL_VELOCITY-MU*GRAVITY*END_TIME)
    final_velocity=rows[-1]["velocity_x_m_s"]
    velocity_error=abs(final_velocity-theoretical_velocity)/INITIAL_VELOCITY
    block_mass=DENSITY*WIDTH*HEIGHT*THICKNESS
    for row in rows:
        row["friction_force_from_inertial_balance_n"]=-block_mass*row["acceleration_x_m_s2"]
    median_friction_force=statistics.median(r["friction_force_from_inertial_balance_n"] for r in rows[5:])
    theoretical_friction_force=MU*block_mass*GRAVITY
    write_csv(HISTORY,rows)
    svg_plot(PLOT,[([r["time_s"] for r in rows],[r["velocity_x_m_s"] for r in rows],"MAPDL velocity"),([0,END_TIME],[INITIAL_VELOCITY,theoretical_velocity],"Coulomb theory")],"Sliding block with Coulomb friction","Time (s)","Velocity (m/s)")
    checks={"history_available":len(rows)>=50,"contact_closed":max(r["contact_status"] for r in rows)>=1,"contact_pressure_positive":max(r["max_contact_pressure_pa"] for r in rows)>100,"friction_force_matches_coulomb":abs(median_friction_force-theoretical_friction_force)/theoretical_friction_force<0.15,"sliding_decelerates":0<final_velocity<INITIAL_VELOCITY,"coulomb_velocity_sanity":velocity_error<0.20,"finite_results":all(math.isfinite(v) for r in rows for v in r.values())}
    payload={"status":"PASS" if all(checks.values()) else "FAIL","timestamp_utc":datetime.now(timezone.utc).isoformat(),"analysis":"MAPDL implicit full transient with PLANE182/TARGE169/CONTA172 frictional contact","model":{"block_width_m":WIDTH,"block_height_m":HEIGHT,"thickness_m":THICKNESS,"density_kg_m3":DENSITY,"block_mass_kg":block_mass,"friction_coefficient":MU,"gravity_m_s2":GRAVITY,"initial_velocity_m_s":INITIAL_VELOCITY,"end_time_s":END_TIME,"nominal_time_step_s":TIME_STEP},"results":{"sample_count":len(rows),"final_displacement_x_m":rows[-1]["displacement_x_m"],"final_velocity_x_m_s":final_velocity,"theoretical_final_velocity_m_s":theoretical_velocity,"velocity_error_fraction_of_initial":velocity_error,"maximum_contact_pressure_pa":max(r["max_contact_pressure_pa"] for r in rows),"maximum_total_contact_stress_pa":max(abs(r["max_total_contact_stress_pa"]) for r in rows),"maximum_contact_status":max(r["contact_status"] for r in rows),"median_friction_force_from_inertial_balance_n":median_friction_force,"theoretical_coulomb_friction_force_n":theoretical_friction_force},"checks":checks,"files":{"history_csv":str(HISTORY),"plot_svg":str(PLOT),"solver_output":str(SOLVER_OUT)}}
    write_json(RESULT,payload);print(payload,flush=True);print("CASE C",payload["status"],flush=True)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__":raise SystemExit(main())
