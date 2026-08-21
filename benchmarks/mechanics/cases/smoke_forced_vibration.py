"""MAPDL harmonic-response smoke test for an SDOF oscillator."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from dynamics_smoke_common import OUT, apdl_path, read_numeric_csv, run_mapdl, svg_plot, write_csv, write_json


MASS = 1.0
STIFFNESS = 100.0
DAMPING = 2.0
FORCE = 1.0
FAR_FREQUENCY = 0.50
NEAR_FREQUENCY = math.sqrt(STIFFNESS/MASS)/(2*math.pi)

INPUT = OUT / "forced_vibration.inp"
SOLVER_OUT = OUT / "forced_vibration_solver.out"
RAW = OUT / "forced_vibration_raw.csv"
HISTORY = OUT / "forced_vibration_history.csv"
RESULT = OUT / "forced_vibration_results.json"
PLOT = OUT / "forced_vibration_amplitudes.svg"


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
F,2,FX,{FORCE}
FINISH
/SOLU
ANTYPE,HARMIC
HROPT,FULL
KBC,1
HARFRQ,{FAR_FREQUENCY}
NSUBST,1
SOLVE
HARFRQ,{NEAR_FREQUENCY}
NSUBST,1
SOLVE
FINISH
/POST1
*CFOPEN,'{apdl_path(RAW.with_suffix(''))}','csv'
SET,1,1,,0
*GET,UR1,NODE,2,U,X
SET,1,1,,1
*GET,UI1,NODE,2,U,X
AMP1=SQRT(UR1*UR1+UI1*UI1)
*VWRITE,{FAR_FREQUENCY},UR1,UI1,AMP1
(E20.12,',',E20.12,',',E20.12,',',E20.12)
SET,2,1,,0
*GET,UR2,NODE,2,U,X
SET,2,1,,1
*GET,UI2,NODE,2,U,X
AMP2=SQRT(UR2*UR2+UI2*UI2)
*VWRITE,{NEAR_FREQUENCY},UR2,UI2,AMP2
(E20.12,',',E20.12,',',E20.12,',',E20.12)
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def theory(frequency: float) -> float:
    omega = 2*math.pi*frequency
    return FORCE/math.sqrt((STIFFNESS-MASS*omega*omega)**2+(DAMPING*omega)**2)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for path in (INPUT,SOLVER_OUT,RAW,HISTORY,RESULT,PLOT):
        path.unlink(missing_ok=True)
    INPUT.write_text(apdl(),encoding="ascii")
    if run_mapdl("forced_vibration",INPUT,SOLVER_OUT):
        return 1
    rows=read_numeric_csv(RAW,["frequency_hz","real_displacement_m","imag_displacement_m","amplitude_m"])
    if len(rows)!=2:
        raise RuntimeError(f"Expected two harmonic results, got {rows!r}")
    for row in rows:
        row["theory_amplitude_m"]=theory(row["frequency_hz"])
        row["relative_error"]=abs(row["amplitude_m"]-row["theory_amplitude_m"])/row["theory_amplitude_m"]
    write_csv(HISTORY,rows)
    svg_plot(PLOT,[([r["frequency_hz"] for r in rows],[1000*r["amplitude_m"] for r in rows],"MAPDL"),([r["frequency_hz"] for r in rows],[1000*r["theory_amplitude_m"] for r in rows],"Theory")],"Forced-vibration response","Frequency (Hz)","Amplitude (mm)")
    ratio=rows[1]["amplitude_m"]/rows[0]["amplitude_m"]
    checks={"two_frequencies_solved":len(rows)==2,"finite_positive_amplitudes":all(r["amplitude_m"]>0 and math.isfinite(r["amplitude_m"]) for r in rows),"frequency_response_matches_theory":max(r["relative_error"] for r in rows)<0.02,"near_resonance_amplified":ratio>3.0}
    payload={"status":"PASS" if all(checks.values()) else "FAIL","timestamp_utc":datetime.now(timezone.utc).isoformat(),"analysis":"MAPDL full Harmonic Response; MASS21 + COMBIN14","model":{"mass_kg":MASS,"stiffness_n_m":STIFFNESS,"damping_n_s_m":DAMPING,"force_amplitude_n":FORCE,"natural_frequency_hz":NEAR_FREQUENCY,"far_frequency_hz":FAR_FREQUENCY,"near_frequency_hz":NEAR_FREQUENCY},"results":{"far_amplitude_m":rows[0]["amplitude_m"],"near_amplitude_m":rows[1]["amplitude_m"],"near_to_far_amplitude_ratio":ratio,"maximum_relative_error":max(r["relative_error"] for r in rows)},"checks":checks,"files":{"history_csv":str(HISTORY),"plot_svg":str(PLOT),"solver_output":str(SOLVER_OUT)}}
    write_json(RESULT,payload)
    print(payload,flush=True)
    print("CASE E",payload["status"],flush=True)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
