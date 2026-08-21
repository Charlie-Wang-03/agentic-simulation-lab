"""Focused Phase-0 probe of harmonic FLUID30 perfectly matched layers."""

from __future__ import annotations

from pathlib import Path

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, complex_metrics, ensure_dirs, read_numeric_rows, run_apdl, write_json


CASE="phase0_pml"
FREQ=300.0


def build_apdl(path:Path)->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
ET,2,FLUID30,,1,,1
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,{SOUND_SPEED}
BLOCK,0,0.8,0,0.1,0,0.1
BLOCK,0.8,1.2,0,0.1,0,0.1
VGLUE,ALL
MSHKEY,1
ESIZE,0.025
VSEL,S,LOC,X,0,0.79
TYPE,1
MAT,1
ESYS,0
VMESH,ALL
VSEL,S,LOC,X,0.81,1.2
TYPE,2
MAT,1
ESYS,0
VMESH,ALL
ALLSEL,ALL
NSEL,S,LOC,X,0
D,ALL,PRES,1,0
ALLSEL,ALL
NSEL,S,LOC,X,1.2
D,ALL,PRES,0,0
ALLSEL,ALL
PMLOPT,0,ONE,1.E-3
NSEL,S,LOC,X,0.4
*GET,N1,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,0.7
*GET,N2,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,0.9
*GET,N3,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,1.1
*GET,N4,NODE,0,NUM,MIN
ALLSEL,ALL
/SOLU
ANTYPE,HARM
HROPT,FULL
HARFRQ,{FREQ}
NSUBST,1
SOLVE
FINISH
/POST1
SET,LAST,,,0
*GET,R1,NODE,N1,PRES
*GET,R2,NODE,N2,PRES
*GET,R3,NODE,N3,PRES
*GET,R4,NODE,N4,PRES
SET,LAST,,,1
*GET,I1,NODE,N1,PRES
*GET,I2,NODE,N2,PRES
*GET,I3,NODE,N3,PRES
*GET,I4,NODE,N4,PRES
*CFOPEN,'{apdl_stem(path)}','csv'
*VWRITE,R1,I1,R2,I2,R3,I3,R4,I4
(E22.14,7(',',E22.14))
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main()->int:
    out,_=ensure_dirs(CASE); raw=out/"pml_probes.csv"; raw.unlink(missing_ok=True)
    evidence=run_apdl(CASE,build_apdl(raw),timeout=240)
    rows=read_numeric_rows(raw,["r1","i1","r2","i2","r3","i3","r4","i4"])
    if len(rows)!=1: raise RuntimeError("PML probe extraction failed")
    r=rows[0]; amps=[complex_metrics(r[f"r{i}"],r[f"i{i}"])[0] for i in range(1,5)]
    checks={"finite_nonzero_solution":all(x>0 for x in amps),"attenuation_inside_pml":amps[3]<amps[2],"pml_end_strongly_attenuated":amps[3]<0.3*amps[1]}
    payload={"phase":"0","capability":"harmonic acoustic PML","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261","element":"FLUID30 KEYOPT(4)=1","frequency_hz":FREQ,"pml":{"coordinate_system":0,"layers":16,"target_reflection":1e-3,"exterior_pressure":"zero"},"probe_x_m":[0.4,0.7,0.9,1.1],"pressure_amplitude_pa":amps,"checks":checks,"files":[str(raw.resolve()),evidence["solver_output"]]}
    write_json(out/"pml_results.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
