"""Case E: 3-D point source with rigid and MAPDL INF radiation boundaries."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, complex_metrics, ensure_dirs, read_numeric_rows, run_apdl, spl_db, svg_plot, write_json


CASE="case_e_radiation"
HALF=1.0
DX=0.10
FREQ=500.0
RADII=[0.2,0.4,0.6,0.8]


def probe_setup()->str:
    lines=[]
    for i,r in enumerate(RADII,1):
        lines += [f"NSEL,S,LOC,X,{r}","NSEL,R,LOC,Y,0","NSEL,R,LOC,Z,0",f"*GET,P{i},NODE,0,NUM,MIN","ALLSEL,ALL"]
    return "\n".join(lines)


def solve_export(path:Path,label:int)->list[str]:
    gets=[]; args=[]
    for i in range(1,len(RADII)+1):
        gets += [f"*GET,R{i},NODE,P{i},PRES"]
    gets_im=[]
    for i in range(1,len(RADII)+1): gets_im += [f"*GET,I{i},NODE,P{i},PRES"]
    for i in range(1,len(RADII)+1): args += [f"R{i}",f"I{i}"]
    return ["/SOLU","ANTYPE,HARM","HROPT,FULL",f"HARFRQ,{FREQ}","NSUBST,1","KBC,1","SOLVE","FINISH","/POST1","SET,LAST,,,0",*gets,"SET,LAST,,,1",*gets_im,f"*CFOPEN,'{apdl_stem(path)}','csv',,APPEND",f"*VWRITE,{label},"+",".join(args),"(F8.0,8(',',E22.14))","*CFCLOS","FINISH"]


def build_apdl(path:Path)->str:
    lines=[f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,{SOUND_SPEED}
MP,DMPR,1,0.002
BLOCK,{-HALF},{HALF},{-HALF},{HALF},{-HALF},{HALF}
MSHKEY,1
ESIZE,{DX}
TYPE,1
MAT,1
VMESH,ALL
NSEL,S,LOC,X,0
NSEL,R,LOC,Y,0
NSEL,R,LOC,Z,0
*GET,SRC,NODE,0,NUM,MIN
ALLSEL,ALL
BF,SRC,MASS,1,0
{probe_setup()}
*CFOPEN,'{apdl_stem(path)}','csv'
*VWRITE,-1,0,0,0,0,0,0,0,0
(F8.0,8(',',E22.14))
*CFCLOS"""]
    lines += solve_export(path,0)
    lines += ["/PREP7"]
    for axis in "XYZ":
        lines += [f"NSEL,S,LOC,{axis},{-HALF}","SF,ALL,INF","ALLSEL,ALL",f"NSEL,S,LOC,{axis},{HALF}","SF,ALL,INF","ALLSEL,ALL"]
    lines += ["FINISH"]+solve_export(path,1)+["/EXIT,NOSAVE"]
    return "\n".join(lines)+"\n"


def main()->int:
    out,_=ensure_dirs(CASE); csv_path=out/"rigid_vs_radiation_radial.csv"; csv_path.unlink(missing_ok=True)
    evidence=run_apdl(CASE,build_apdl(csv_path),timeout=360)
    columns=["boundary"]+[name for i in range(1,5) for name in (f"p{i}_real",f"p{i}_imag")]
    rows=[r for r in read_numeric_rows(csv_path,columns) if r["boundary"]>=0]
    if len(rows)!=2: raise RuntimeError(f"Expected two radiation comparisons, got {len(rows)}")
    data={}
    for row in rows:
        amps=[]
        for i in range(1,5): amps.append(complex_metrics(row[f"p{i}_real"],row[f"p{i}_imag"])[0])
        data[int(row["boundary"])]=amps
    rigid,rad=data[0],data[1]
    rigid_pr=np.asarray(rigid)*np.asarray(RADII); rad_pr=np.asarray(rad)*np.asarray(RADII)
    rigid_cv=float(np.std(rigid_pr)/np.mean(rigid_pr)); rad_cv=float(np.std(rad_pr)/np.mean(rad_pr))
    decay_ratio=rad[-1]/rad[0]; theory_ratio=RADII[0]/RADII[-1]
    decay_error=abs(decay_ratio-theory_ratio)/theory_ratio
    plot=out/"radiation_pressure_decay.svg"
    svg_plot(plot,[(RADII,rigid,"rigid box"),(RADII,rad,"INF radiation")],"Radial pressure decay","Radius (m)","Pressure amplitude (Pa)")
    checks={"two_boundary_models_solved":len(rows)==2,"radiation_decay_error_below_25pct":decay_error<0.25,"radiation_pr_consistent":rad_cv<0.20,"radiation_reduces_artificial_reflection":rad_cv<rigid_cv}
    far_r=10.0; far_p=rad[-1]*RADII[-1]/far_r
    payload={"case":"E","title":"Open acoustic field with radiation boundary","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261","element":"FLUID30 KEYOPT(2)=1","analysis_type":"full harmonic acoustics","geometry":{"air_box_side_m":2*HALF,"source":"interior point mass source","boundaries":["natural rigid","SF,INF radiation"]},"acoustic_material":{"density_kg_m3":AIR_DENSITY,"sound_speed_m_s":SOUND_SPEED},"mesh":{"nominal_size_m":DX},"frequency_hz":FREQ,"results":{"radii_m":RADII,"rigid_pressure_pa":rigid,"radiation_pressure_pa":rad,"radiation_spl_db":[spl_db(x) for x in rad],"pressure_decay_ratio":decay_ratio,"radiation_pr_coefficient_of_variation":rad_cv,"rigid_pr_coefficient_of_variation":rigid_cv,"spherical_extrapolated_pressure_at_10m_pa":far_p,"spherical_extrapolated_spl_at_10m_db":spl_db(far_p)},"theory":{"far_field_trend":"|p| proportional to 1/r","expected_decay_ratio":theory_ratio},"errors":{"radial_decay_relative_error":decay_error},"checks":checks,"limitations":["The 10 m value is a spherical-spreading extrapolation from the outer FEM probe, not a PRFAR native far-field evaluation."],"files":[str(csv_path.resolve()),str(plot.resolve()),evidence["solver_output"]]}
    write_json(out/"case_e_results.json",payload); print(payload)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
