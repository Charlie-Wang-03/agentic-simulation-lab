"""MAPDL transient smoke test for a one-DOF mass-spring-damper system."""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone

from dynamics_smoke_common import OUT, apdl_path, read_numeric_csv, run_mapdl, svg_plot, write_csv, write_json


MASS = 1.0
STIFFNESS = 100.0
DAMPING = 2.0
INITIAL_DISPLACEMENT = 0.010
INITIAL_VELOCITY = 0.0
END_TIME = 3.0
TIME_STEP = 0.005

INPUT = OUT / "spring_damper.inp"
SOLVER_OUT = OUT / "spring_damper_solver.out"
RAW = OUT / "spring_damper_raw.csv"
HISTORY = OUT / "spring_damper_history.csv"
RESULT = OUT / "spring_damper_results.json"
PLOT = OUT / "spring_damper_response.svg"


def apdl() -> str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,MASS21
R,1,{MASS},{MASS},{MASS},0,0,0
TYPE,1
REAL,1
N,2,1,0,0
E,2
ET,2,COMBIN14
KEYOPT,2,1,0
R,2,{STIFFNESS},{DAMPING}
TYPE,2
REAL,2
N,1,0,0,0
E,1,2
D,1,ALL,0
D,2,UY,0
D,2,UZ,0
D,2,ROTX,0
D,2,ROTY,0
D,2,ROTZ,0
FINISH
/SOLU
ANTYPE,TRANS
TRNOPT,FULL
TIMINT,ON
KBC,1
AUTOTS,OFF
DELTIM,{TIME_STEP}
OUTRES,ALL,ALL
IC,2,UX,{INITIAL_DISPLACEMENT},{INITIAL_VELOCITY}
TIME,{END_TIME}
SOLVE
FINISH
/POST1
*GET,NSETS,ACTIVE,0,SET,NSET
*CFOPEN,'{apdl_path(RAW.with_suffix(''))}','csv'
*DO,II,1,NSETS
SET,1,II
*GET,TT,ACTIVE,0,SET,TIME
*GET,UU,NODE,2,U,X
*GET,VV,NODE,2,V,X
*GET,AA,NODE,2,A,X
*VWRITE,TT,UU,VV,AA
(E20.12,',',E20.12,',',E20.12,',',E20.12)
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for path in (INPUT, SOLVER_OUT, RAW, HISTORY, RESULT, PLOT):
        path.unlink(missing_ok=True)
    INPUT.write_text(apdl(), encoding="ascii")
    if run_mapdl("spring_damper", INPUT, SOLVER_OUT):
        return 1
    rows = read_numeric_csv(RAW, ["time_s", "displacement_m", "velocity_m_s", "acceleration_m_s2"])
    if len(rows) < 100:
        raise RuntimeError(f"Expected transient history, got {len(rows)} points")
    wn = math.sqrt(STIFFNESS/MASS)
    zeta = DAMPING/(2*math.sqrt(STIFFNESS*MASS))
    wd = wn*math.sqrt(1-zeta*zeta)
    for row in rows:
        t = row["time_s"]
        row["theory_displacement_m"] = math.exp(-zeta*wn*t)*(INITIAL_DISPLACEMENT*math.cos(wd*t)+(INITIAL_VELOCITY+zeta*wn*INITIAL_DISPLACEMENT)/wd*math.sin(wd*t))
    rmse = math.sqrt(sum((r["displacement_m"]-r["theory_displacement_m"])**2 for r in rows)/len(rows))
    normalized_rmse = rmse/INITIAL_DISPLACEMENT
    write_csv(HISTORY, rows)
    svg_plot(PLOT, [([r["time_s"] for r in rows],[1000*r["displacement_m"] for r in rows],"MAPDL"),([r["time_s"] for r in rows],[1000*r["theory_displacement_m"] for r in rows],"Theory")], "Mass-spring-damper free response", "Time (s)", "Displacement (mm)")
    checks = {"solver_history":len(rows)>=100,"finite_response":all(math.isfinite(v) for r in rows for v in r.values()),"decaying_response":abs(rows[-1]["displacement_m"])<0.2*INITIAL_DISPLACEMENT,"theory_rmse_below_2_percent":normalized_rmse<0.02}
    payload = {"status":"PASS" if all(checks.values()) else "FAIL","timestamp_utc":datetime.now(timezone.utc).isoformat(),"analysis":"MAPDL full transient; MASS21 + COMBIN14","model":{"mass_kg":MASS,"stiffness_n_m":STIFFNESS,"damping_n_s_m":DAMPING,"initial_displacement_m":INITIAL_DISPLACEMENT,"initial_velocity_m_s":INITIAL_VELOCITY,"end_time_s":END_TIME,"time_step_s":TIME_STEP},"theory":{"undamped_natural_frequency_rad_s":wn,"undamped_natural_frequency_hz":wn/(2*math.pi),"damping_ratio":zeta,"damped_natural_frequency_hz":wd/(2*math.pi)},"results":{"sample_count":len(rows),"maximum_abs_displacement_m":max(abs(r["displacement_m"]) for r in rows),"maximum_abs_velocity_m_s":max(abs(r["velocity_m_s"]) for r in rows),"maximum_abs_acceleration_m_s2":max(abs(r["acceleration_m_s2"]) for r in rows),"normalized_displacement_rmse":normalized_rmse},"checks":checks,"files":{"history_csv":str(HISTORY),"plot_svg":str(PLOT),"solver_output":str(SOLVER_OUT)}}
    write_json(RESULT,payload)
    print(payload, flush=True)
    print("CASE A",payload["status"],flush=True)
    return 0 if payload["status"]=="PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
