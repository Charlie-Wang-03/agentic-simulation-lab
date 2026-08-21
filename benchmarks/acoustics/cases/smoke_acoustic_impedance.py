"""Case H: rigid versus impedance-terminated acoustic tube."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, complex_metrics, ensure_dirs, read_numeric_rows, run_apdl, svg_plot, write_json


CASE="case_h_impedance"
LENGTH,WIDTH,DX=1.0,0.05,0.025
FREQUENCIES=np.arange(210.0,501.0,10.0)
X1,X2=0.70,0.80


def preamble()->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,{SOUND_SPEED}
MP,DMPR,1,0.003
BLOCK,0,{LENGTH},0,{WIDTH},0,{WIDTH}
MSHKEY,1
ESIZE,{DX}
TYPE,1
MAT,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,PRES,1,0
ALLSEL,ALL
NSEL,S,LOC,X,{X1}
*GET,N1,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,{X2}
*GET,N2,NODE,0,NUM,MIN
ALLSEL,ALL
"""


def solve_lines(csv_path:Path,label:int)->list[str]:
    lines=[]
    for f in FREQUENCIES:
        lines += ["/SOLU","ANTYPE,HARM","HROPT,FULL",f"HARFRQ,{f}","NSUBST,1","KBC,1","SOLVE","FINISH","/POST1","SET,LAST,,,0","*GET,R1,NODE,N1,PRES","*GET,R2,NODE,N2,PRES","SET,LAST,,,1","*GET,I1,NODE,N1,PRES","*GET,I2,NODE,N2,PRES",f"*CFOPEN,'{apdl_stem(csv_path)}','csv',,APPEND",f"*VWRITE,{label},{f},R1,I1,R2,I2","(F8.0,',',F12.4,4(',',E22.14))","*CFCLOS","FINISH"]
    return lines


def build_apdl(csv_path:Path)->str:
    lines=[preamble(),f"*CFOPEN,'{apdl_stem(csv_path)}','csv'","*VWRITE,-1,0,0,0,0,0","(F8.0,',',F12.4,4(',',E22.14))","*CFCLOS"]
    lines += solve_lines(csv_path,0)
    lines += ["/PREP7",f"NSEL,S,LOC,X,{LENGTH}",f"SF,ALL,IMPD,{AIR_DENSITY*SOUND_SPEED},0","ALLSEL,ALL","FINISH"]
    lines += solve_lines(csv_path,1)
    return "\n".join(lines+["/EXIT,NOSAVE"]) + "\n"


def reflection(p1:complex,p2:complex,f:float)->float:
    k=2*math.pi*f/SOUND_SPEED
    mat=np.array([[np.exp(-1j*k*X1),np.exp(1j*k*X1)],[np.exp(-1j*k*X2),np.exp(1j*k*X2)]],dtype=complex)
    inc,refl=np.linalg.solve(mat,np.array([p1,p2],dtype=complex))
    return float(abs(refl/inc))


def main()->int:
    out,_=ensure_dirs(CASE); csv_path=out/"rigid_vs_impedance.csv"; csv_path.unlink(missing_ok=True)
    evidence=run_apdl(CASE,build_apdl(csv_path),timeout=360)
    rows=[r for r in read_numeric_rows(csv_path,["termination","frequency_hz","p1_real","p1_imag","p2_real","p2_imag"]) if r["termination"]>=0]
    rigid=[r for r in rows if int(r["termination"])==0]; matched=[r for r in rows if int(r["termination"])==1]
    for r in rows:
        p1=complex(r["p1_real"],r["p1_imag"]); p2=complex(r["p2_real"],r["p2_imag"])
        r["p1_amplitude_pa"],_=complex_metrics(r["p1_real"],r["p1_imag"])
        r["reflection_magnitude"]=reflection(p1,p2,r["frequency_hz"])
    rigid_R=float(np.median([r["reflection_magnitude"] for r in rigid])); matched_R=float(np.median([r["reflection_magnitude"] for r in matched]))
    theoretical_R=abs((AIR_DENSITY*SOUND_SPEED-AIR_DENSITY*SOUND_SPEED)/(AIR_DENSITY*SOUND_SPEED+AIR_DENSITY*SOUND_SPEED))
    rigid_peak=max(r["p1_amplitude_pa"] for r in rigid); matched_peak=max(r["p1_amplitude_pa"] for r in matched)
    plot=out/"rigid_vs_impedance.svg"
    svg_plot(plot,[([r["frequency_hz"] for r in rigid],[r["p1_amplitude_pa"] for r in rigid],"rigid"),([r["frequency_hz"] for r in matched],[r["p1_amplitude_pa"] for r in matched],"Z=rho*c")],"Rigid vs matched termination","Frequency (Hz)","Pressure amplitude (Pa)")
    checks={"both_sweeps_complete":len(rigid)==len(FREQUENCIES) and len(matched)==len(FREQUENCIES),"rigid_reflection_near_unity":0.8<rigid_R<1.2,"matched_reflection_below_0p15":matched_R<0.15,"resonance_reduced":matched_peak<0.7*rigid_peak}
    payload={"case":"H","title":"Acoustic impedance and absorbing boundary","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261","element":"FLUID30 KEYOPT(2)=1","analysis_type":"full harmonic acoustics","geometry":{"length_m":LENGTH,"terminations":["natural rigid","IMPD=rho*c"]},"acoustic_material":{"density_kg_m3":AIR_DENSITY,"sound_speed_m_s":SOUND_SPEED,"characteristic_impedance_pa_s_m":AIR_DENSITY*SOUND_SPEED},"mesh":{"nominal_size_m":DX},"results":{"median_rigid_reflection_magnitude":rigid_R,"median_matched_reflection_magnitude":matched_R,"rigid_peak_pressure_pa":rigid_peak,"matched_peak_pressure_pa":matched_peak},"theory":{"formula":"R=(Z-rho*c)/(Z+rho*c)","matched_reflection_magnitude":theoretical_R},"errors":{"matched_absolute_reflection_error":abs(matched_R-theoretical_R)},"checks":checks,"files":[str(csv_path.resolve()),str(plot.resolve()),evidence["solver_output"]]}
    write_json(out/"case_h_results.json",payload); print(payload)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
