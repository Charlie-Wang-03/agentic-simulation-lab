"""Case D: transient pressure pulse propagation in a straight acoustic domain."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, ensure_dirs, read_numeric_rows, run_apdl, svg_plot, write_json


CASE = "case_d_transient"
LENGTH, WIDTH, DX = 1.0, 0.02, 0.01
DT, NSTEP = 2.0e-5, 150


def build_apdl(history: Path, snapshots: Path) -> str:
    table = []
    for i in range(1, NSTEP+2):
        t = (i-1)*DT
        p = math.exp(-((t-3.0e-4)/(9.0e-5))**2)
        table += [f"PULSE({i},0)={t:.12g}", f"PULSE({i},1)={p:.12g}"]
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY:.12g}
MP,SONC,1,{SOUND_SPEED:.12g}
BLOCK,0,{LENGTH},0,{WIDTH},0,{WIDTH}
MSHKEY,1
ESIZE,{DX}
TYPE,1
MAT,1
VMESH,ALL
ALLSEL,ALL
NSEL,S,LOC,X,0.25
*GET,P1,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,0.50
*GET,P2,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,0.75
*GET,P3,NODE,0,NUM,MIN
ALLSEL,ALL
*DIM,PULSE,TABLE,{NSTEP+1},1,1,TIME
{chr(10).join(table)}
NSEL,S,LOC,X,0
D,ALL,PRES,%PULSE%
ALLSEL,ALL
/SOLU
ANTYPE,TRANS
TRNOPT,FULL
TIMINT,ON
AUTOTS,OFF
TIME,{NSTEP*DT:.12g}
DELTIM,{DT:.12g},{DT:.12g},{DT:.12g}
KBC,0
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
*CFOPEN,'{apdl_stem(history)}','csv'
*DO,II,1,{NSTEP}
SET,1,II
*GET,TT,ACTIVE,0,SET,TIME
*GET,V1,NODE,P1,PRES
*GET,V2,NODE,P2,PRES
*GET,V3,NODE,P3,PRES
*VWRITE,TT,V1,V2,V3
(E22.14,3(',',E22.14))
*ENDDO
*CFCLOS
*CFOPEN,'{apdl_stem(snapshots)}','csv'
*DO,JJ,55,135,20
SET,1,JJ
*GET,TT,ACTIVE,0,SET,TIME
NSEL,S,LOC,Y,0
NSEL,R,LOC,Z,0
*GET,NC,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*DO,KK,1,NC
*GET,XX,NODE,NID,LOC,X
*GET,PP,NODE,NID,PRES
*VWRITE,TT,NID,XX,PP
(E22.14,',',F12.0,2(',',E22.14))
NID=NDNEXT(NID)
*ENDDO
ALLSEL,ALL
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main() -> int:
    out,_=ensure_dirs(CASE)
    history,snapshots=out/"probe_history.csv",out/"pressure_snapshots.csv"
    for p in (history,snapshots): p.unlink(missing_ok=True)
    evidence=run_apdl(CASE,build_apdl(history,snapshots),timeout=300)
    rows=read_numeric_rows(history,["time_s","p_x025_pa","p_x050_pa","p_x075_pa"])
    fields=read_numeric_rows(snapshots,["time_s","node_id","x_m","pressure_pa"])
    if len(rows)<NSTEP-2: raise RuntimeError(f"Expected transient history, got {len(rows)} rows")
    t1=max(rows,key=lambda r:abs(r["p_x025_pa"]))["time_s"]
    t3=max(rows,key=lambda r:abs(r["p_x075_pa"]))["time_s"]
    measured_speed=0.50/(t3-t1)
    error=abs(measured_speed-SOUND_SPEED)/SOUND_SPEED
    plot=out/"transient_probe_history.svg"
    times=[r["time_s"] for r in rows]
    svg_plot(plot,[(times,[r["p_x025_pa"] for r in rows],"x=0.25 m"),(times,[r["p_x050_pa"] for r in rows],"x=0.50 m"),(times,[r["p_x075_pa"] for r in rows],"x=0.75 m")],"Transient acoustic pulse propagation","Time (s)","Pressure (Pa)")
    snapshot_times=sorted(set(round(r["time_s"],12) for r in fields))
    checks={"history_complete":len(rows)>=NSTEP-2,"snapshots_saved":len(snapshot_times)==5,"causal_probe_order":t3>t1,"wave_speed_error_below_8pct":error<0.08,"pressure_nonzero":max(abs(r["p_x050_pa"]) for r in rows)>1e-4}
    payload={"case":"D","title":"Transient acoustic wave propagation","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261","element":"FLUID30 KEYOPT(2)=1","analysis_type":"full transient acoustics, pressure formulation","geometry":{"length_m":LENGTH,"width_m":WIDTH,"boundary":"Gaussian prescribed-pressure pulse at x=0; other faces natural rigid"},"acoustic_material":{"density_kg_m3":AIR_DENSITY,"sound_speed_m_s":SOUND_SPEED},"mesh":{"nominal_size_m":DX},"time_integration":{"time_step_s":DT,"steps":NSTEP,"end_time_s":NSTEP*DT},"results":{"probe_peak_time_x025_s":t1,"probe_peak_time_x075_s":t3,"measured_wave_speed_m_s":measured_speed,"snapshot_times_s":snapshot_times},"theory":{"relation":"distance=c*time","sound_speed_m_s":SOUND_SPEED},"errors":{"relative_wave_speed_error":error},"checks":checks,"files":[str(history.resolve()),str(snapshots.resolve()),str(plot.resolve()),evidence["solver_output"]]}
    write_json(out/"case_d_results.json",payload)
    print(payload)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
