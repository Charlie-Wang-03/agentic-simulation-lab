"""Case G: strong two-way matrix-coupled flexible plate and acoustic cavity modes."""

from __future__ import annotations

import math
from pathlib import Path

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, classify_solver_restriction, ensure_dirs, read_numeric_rows, run_apdl, write_json


CASE="case_g_coupled"
SIDE,HEIGHT,THICKNESS,DX=0.40,0.30,0.002,0.04
E,NU,RHO_S=200e9,0.3,7850.0
NMODES=6


def modal_export(path:Path)->str:
    return f"""/POST1
*CFOPEN,'{apdl_stem(path)}','csv'
*DO,II,1,{NMODES}
SET,1,II
*GET,FF,ACTIVE,0,SET,FREQ
*VWRITE,II,FF
(F12.0,',',E22.14)
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def structure_apdl(path:Path)->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SHELL181
SECTYPE,1,SHELL
SECDATA,{THICKNESS}
MP,EX,1,{E}
MP,PRXY,1,{NU}
MP,DENS,1,{RHO_S}
RECTNG,0,{SIDE},0,{SIDE}
ESIZE,{DX}
MSHKEY,1
TYPE,1
MAT,1
SECNUM,1
AMESH,ALL
NSEL,S,LOC,X,0
NSEL,A,LOC,X,{SIDE}
NSEL,A,LOC,Y,0
NSEL,A,LOC,Y,{SIDE}
D,ALL,ALL,0
ALLSEL,ALL
/SOLU
ANTYPE,MODAL
MODOPT,LANB,{NMODES},10,1500
MXPAND,{NMODES},,,,YES
SOLVE
FINISH
{modal_export(path)}"""


def acoustic_apdl(path:Path)->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,{SOUND_SPEED}
BLOCK,0,{SIDE},0,{SIDE},0,{HEIGHT}
MSHKEY,1
ESIZE,{DX}
TYPE,1
MAT,1
VMESH,ALL
/SOLU
ANTYPE,MODAL
MODOPT,LANB,{NMODES},10,1500
MXPAND,{NMODES},,,,YES
SOLVE
FINISH
{modal_export(path)}"""


def coupled_apdl(path:Path,field:Path)->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30
KEYOPT,1,2,0
ET,2,SHELL181
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,{SOUND_SPEED}
MP,EX,2,{E}
MP,PRXY,2,{NU}
MP,DENS,2,{RHO_S}
SECTYPE,1,SHELL
SECDATA,{THICKNESS}
BLOCK,0,{SIDE},0,{SIDE},0,{HEIGHT}
MSHKEY,1
ESIZE,{DX}
TYPE,1
MAT,1
VMESH,ALL
ASEL,S,LOC,Z,0
TYPE,2
MAT,2
SECNUM,1
AMESH,ALL
ALLSEL,ALL
NSEL,S,LOC,Z,0
SF,ALL,FSI
CM,FSI_NODES,NODE
ALLSEL,ALL
NSEL,S,ALL
NSEL,U,LOC,Z,0
D,ALL,UX,0
D,ALL,UY,0
D,ALL,UZ,0
ALLSEL,ALL
NSEL,S,LOC,X,0
NSEL,A,LOC,X,{SIDE}
NSEL,A,LOC,Y,0
NSEL,A,LOC,Y,{SIDE}
D,ALL,UX,0
D,ALL,UY,0
D,ALL,UZ,0
D,ALL,ROTX,0
D,ALL,ROTY,0
D,ALL,ROTZ,0
ALLSEL,ALL
/SOLU
ANTYPE,MODAL
MODOPT,UNSYM,{NMODES},10,1500
MXPAND,{NMODES},,,,YES
SOLVE
FINISH
/POST1
*CFOPEN,'{apdl_stem(path)}','csv'
*DO,II,1,{NMODES}
SET,1,II
*GET,FF,ACTIVE,0,SET,FREQ
*VWRITE,II,FF
(F12.0,',',E22.14)
*ENDDO
*CFCLOS
SET,1,1
ALLSEL,ALL
*GET,NC,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_stem(field)}','csv'
*DO,JJ,1,NC
*GET,XX,NODE,NID,LOC,X
*GET,YY,NODE,NID,LOC,Y
*GET,ZZ,NODE,NID,LOC,Z
*GET,PP,NODE,NID,PRES
*GET,UU,NODE,NID,U,Z
*VWRITE,NID,XX,YY,ZZ,PP,UU
(F12.0,5(',',E22.14))
NID=NDNEXT(NID)
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main()->int:
    out,_=ensure_dirs(CASE); sp=out/"structure_only_modes.csv"; ap=out/"acoustic_only_modes.csv"; cp=out/"coupled_modes.csv"; cf=out/"coupled_mode1_fields.csv"
    for p in (sp,ap,cp,cf): p.unlink(missing_ok=True)
    try:
        evs=run_apdl(CASE+"_structure",structure_apdl(sp),timeout=180)
        eva=run_apdl(CASE+"_acoustic",acoustic_apdl(ap),timeout=180)
        evc=run_apdl(CASE+"_system",coupled_apdl(cp,cf),timeout=300)
    except RuntimeError:
        solver_out=(ensure_dirs(CASE+"_system")[0]/f"{CASE}_system.out")
        restriction=classify_solver_restriction(solver_out)
        if restriction:
            payload={"case":"G","title":"Two-way structural-acoustic coupling","status":restriction,"files":[str(solver_out.resolve())]}
            write_json(out/"case_g_results.json",payload); print(payload); return 0
        raise
    s=read_numeric_rows(sp,["mode","frequency_hz"]); a=read_numeric_rows(ap,["mode","frequency_hz"]); c=read_numeric_rows(cp,["mode","frequency_hz"]); field=read_numeric_rows(cf,["node_id","x_m","y_m","z_m","pressure_pa","uz_m"])
    if not s or not a or not c: raise RuntimeError("Missing modal results")
    reference=s+a
    comparisons=[]
    for mode in c:
        nearest=min(reference,key=lambda r:abs(r["frequency_hz"]-mode["frequency_hz"]))
        comparisons.append({"coupled_mode":int(mode["mode"]),"coupled_hz":mode["frequency_hz"],"nearest_uncoupled_hz":nearest["frequency_hz"],"relative_shift":(mode["frequency_hz"]-nearest["frequency_hz"])/nearest["frequency_hz"]})
    max_shift=max(abs(x["relative_shift"]) for x in comparisons)
    pressure_nonzero=any(abs(r["pressure_pa"])>1e-12 for r in field); displacement_nonzero=any(abs(r["uz_m"])>1e-12 for r in field)
    checks={"three_models_solved":len(s)==NMODES and len(a)==NMODES and len(c)==NMODES,"coupled_field_saved":len(field)>100,"acoustic_pressure_in_coupled_mode":pressure_nonzero,"structural_displacement_in_coupled_mode":displacement_nonzero,"coupled_frequency_shift_nonzero":max_shift>1e-5}
    payload={"case":"G","title":"Two-way structural-acoustic coupled cavity and flexible plate","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261","elements":{"structure":"SHELL181","acoustic":"FLUID30 KEYOPT(2)=0"},"analysis_type":"unsymmetric strong matrix-coupled modal acoustics","geometry":{"plate_side_m":SIDE,"plate_thickness_m":THICKNESS,"cavity_height_m":HEIGHT,"interface":"shared nodes flagged SF,FSI"},"materials":{"plate":{"E_pa":E,"nu":NU,"density_kg_m3":RHO_S},"air":{"density_kg_m3":AIR_DENSITY,"sound_speed_m_s":SOUND_SPEED}},"mesh":{"nominal_size_m":DX,"coupled_field_nodes":len(field)},"results":{"structure_only_hz":[r["frequency_hz"] for r in s],"acoustic_only_hz":[r["frequency_hz"] for r in a],"coupled_hz":[r["frequency_hz"] for r in c],"comparisons":comparisons,"maximum_nearest_reference_shift":max_shift},"checks":checks,"files":[str(sp.resolve()),str(ap.resolve()),str(cp.resolve()),str(cf.resolve()),evs["solver_output"],eva["solver_output"],evc["solver_output"]]}
    write_json(out/"case_g_results.json",payload); print(payload)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
