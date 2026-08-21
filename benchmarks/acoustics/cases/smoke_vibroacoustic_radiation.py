"""Case F: solved shell vibration driving a one-way acoustic radiation model."""

from __future__ import annotations

import math
from pathlib import Path

from acoustics_common import AIR_DENSITY, SOUND_SPEED, apdl_stem, complex_metrics, ensure_dirs, read_numeric_rows, run_apdl, spl_db, write_json


CASE="case_f_vibroacoustic"
SIDE,THICKNESS,DX,FREQ=0.40,0.002,0.04,300.0
E,NU,RHO_S=200e9,0.3,7850.0


def structural_apdl(path:Path)->str:
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
NSEL,S,LOC,X,{SIDE/2}
NSEL,R,LOC,Y,{SIDE/2}
*GET,CTR,NODE,0,NUM,MIN
ALLSEL,ALL
F,CTR,FZ,1
/SOLU
ANTYPE,HARM
HROPT,FULL
HARFRQ,{FREQ}
NSUBST,1
SOLVE
FINISH
/POST1
SET,LAST,,,0
*GET,UR,NODE,CTR,U,Z
SET,LAST,,,1
*GET,UI,NODE,CTR,U,Z
*CFOPEN,'{apdl_stem(path)}','csv'
*VWRITE,{FREQ},UR,UI
(F14.6,2(',',E22.14))
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def acoustic_apdl(path:Path,field_path:Path,velocity:float,phase:float)->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,{SOUND_SPEED}
BLOCK,0,{SIDE},0,{SIDE},0,{SIDE}
MSHKEY,1
ESIZE,{DX}
TYPE,1
MAT,1
VMESH,ALL
NSEL,S,LOC,Z,0
SF,ALL,SHLD,{velocity},{phase}
ALLSEL,ALL
NSEL,S,LOC,Z,{SIDE}
SF,ALL,INF
ALLSEL,ALL
NSEL,S,LOC,X,0
SF,ALL,INF
ALLSEL,ALL
NSEL,S,LOC,X,{SIDE}
SF,ALL,INF
ALLSEL,ALL
NSEL,S,LOC,Y,0
SF,ALL,INF
ALLSEL,ALL
NSEL,S,LOC,Y,{SIDE}
SF,ALL,INF
ALLSEL,ALL
NSEL,S,LOC,X,{SIDE/2}
NSEL,R,LOC,Y,{SIDE/2}
NSEL,R,LOC,Z,0.08
*GET,P1,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,{SIDE/2}
NSEL,R,LOC,Y,{SIDE/2}
NSEL,R,LOC,Z,0.20
*GET,P2,NODE,0,NUM,MIN
ALLSEL,ALL
NSEL,S,LOC,X,{SIDE/2}
NSEL,R,LOC,Y,{SIDE/2}
NSEL,R,LOC,Z,0.32
*GET,P3,NODE,0,NUM,MIN
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
*GET,R1,NODE,P1,PRES
*GET,R2,NODE,P2,PRES
*GET,R3,NODE,P3,PRES
SET,LAST,,,1
*GET,I1,NODE,P1,PRES
*GET,I2,NODE,P2,PRES
*GET,I3,NODE,P3,PRES
*CFOPEN,'{apdl_stem(path)}','csv'
*VWRITE,{FREQ},R1,I1,R2,I2,R3,I3
(F14.6,6(',',E22.14))
*CFCLOS
SET,LAST,,,0
ALLSEL,ALL
*GET,NC,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
*CFOPEN,'{apdl_stem(field_path)}','csv'
*DO,II,1,NC
*GET,XX,NODE,NID,LOC,X
*GET,YY,NODE,NID,LOC,Y
*GET,ZZ,NODE,NID,LOC,Z
*GET,PP,NODE,NID,PRES
*VWRITE,NID,XX,YY,ZZ,PP
(F12.0,4(',',E22.14))
NID=NDNEXT(NID)
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
"""


def main()->int:
    out,_=ensure_dirs(CASE); sr=out/"structural_response.csv"; ar=out/"acoustic_response.csv"; af=out/"acoustic_pressure_field.csv"
    for p in (sr,ar,af): p.unlink(missing_ok=True)
    evs=run_apdl(CASE+"_structure",structural_apdl(sr),timeout=180)
    srows=read_numeric_rows(sr,["frequency_hz","disp_real_m","disp_imag_m"])
    if len(srows)!=1: raise RuntimeError("Structural response extraction failed")
    u=complex(srows[0]["disp_real_m"],srows[0]["disp_imag_m"]); omega=2*math.pi*FREQ; v=1j*omega*u
    velocity=abs(v); phase=math.degrees(math.atan2(v.imag,v.real))
    eva=run_apdl(CASE+"_acoustic",acoustic_apdl(ar,af,velocity,phase),timeout=240)
    arows=read_numeric_rows(ar,["frequency_hz","p1_real","p1_imag","p2_real","p2_imag","p3_real","p3_imag"]); field=read_numeric_rows(af,["node_id","x_m","y_m","z_m","pressure_pa"])
    if len(arows)!=1: raise RuntimeError("Acoustic response extraction failed")
    amps=[complex_metrics(arows[0][f"p{i}_real"],arows[0][f"p{i}_imag"])[0] for i in range(1,4)]
    area=SIDE*SIDE; power=(amps[-1]/math.sqrt(2))**2/(AIR_DENSITY*SOUND_SPEED)*area
    checks={"structural_response_nonzero":abs(u)>0,"velocity_transferred":velocity>0,"acoustic_response_nonzero":max(amps)>0,"frequency_match":arows[0]["frequency_hz"]==srows[0]["frequency_hz"],"acoustic_field_saved":len(field)>100}
    payload={"case":"F","title":"Vibrating plate acoustic radiation","status":"PASS" if all(checks.values()) else "FAIL","solver":"Ansys MAPDL 261 two-stage one-way chain","elements":{"structure":"SHELL181","acoustic":"FLUID30 KEYOPT(2)=1"},"analysis_type":"structural full harmonic followed by acoustic full harmonic","geometry":{"plate_side_m":SIDE,"plate_thickness_m":THICKNESS,"acoustic_box_height_m":SIDE},"materials":{"plate":{"E_pa":E,"nu":NU,"density_kg_m3":RHO_S},"air":{"density_kg_m3":AIR_DENSITY,"sound_speed_m_s":SOUND_SPEED}},"mesh":{"nominal_size_m":DX,"acoustic_field_nodes":len(field)},"frequency_hz":FREQ,"structure":{"center_displacement_amplitude_m":abs(u),"center_velocity_amplitude_m_s":velocity,"center_acceleration_amplitude_m_s2":omega**2*abs(u),"velocity_phase_deg":phase},"acoustic":{"probe_z_m":[0.08,0.2,0.32],"pressure_amplitude_pa":amps,"spl_db":[spl_db(x) for x in amps],"estimated_radiated_power_w":power},"checks":checks,"limitations":["One-way sequential radiation: the plate is solved structurally, and its center velocity is applied uniformly as SHLD; acoustic back-pressure is intentionally not fed back in Case F.","Radiated power is estimated from the outer-plane pressure using the plane-wave intensity relation."],"files":[str(sr.resolve()),str(ar.resolve()),str(af.resolve()),evs["solver_output"],eva["solver_output"]]}
    write_json(out/"case_f_results.json",payload); print(payload)
    return 0 if payload["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
