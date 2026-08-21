"""Case I: 12 actually solved parametric standing-wave fields for surrogate use."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from acoustics_common import AIR_DENSITY, REFERENCE_PRESSURE_PA, apdl_stem, ensure_dirs, read_numeric_rows, run_apdl, write_json
from acoustics_field_export import export_frequency_domain


CASE="case_i_dataset"
LENGTH,WIDTH,DX=1.0,0.05,0.05
SOUND_SPEEDS=[330.0,343.24,360.0]
FREQUENCIES=[60.0,75.0,95.0,110.0]
PARAMETERS=[(c,f) for c in SOUND_SPEEDS for f in FREQUENCIES]


def preamble()->str:
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,FLUID30,,1
MP,DENS,1,{AIR_DENSITY}
MP,SONC,1,343.24
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
"""


def build_apdl(path:Path)->str:
    lines=[preamble(),f"*CFOPEN,'{apdl_stem(path)}','csv'","*VWRITE,-1,0,0,0,0,0,0,0,0","(F8.0,8(',',E22.14))","*CFCLOS"]
    for idx,(c,f) in enumerate(PARAMETERS):
        lines += ["/PREP7",f"MP,SONC,1,{c}","FINISH","/SOLU","ANTYPE,HARM","HROPT,FULL",f"HARFRQ,{f}","NSUBST,1","KBC,1","SOLVE","FINISH","/POST1","SET,LAST,,,0","ALLSEL,ALL","*GET,NC,NODE,0,COUNT","*GET,NID,NODE,0,NUM,MIN",f"*CFOPEN,'{apdl_stem(path)}','csv',,APPEND","*DO,II,1,NC","*GET,XX,NODE,NID,LOC,X","*GET,YY,NODE,NID,LOC,Y","*GET,ZZ,NODE,NID,LOC,Z","*GET,PR,NODE,NID,PRES","SET,LAST,,,1","*GET,PI,NODE,NID,PRES","SET,LAST,,,0",f"*VWRITE,{idx},{c},{f},NID,XX,YY,ZZ,PR,PI","(F8.0,2(',',F14.6),',',F12.0,5(',',E22.14))","NID=NDNEXT(NID)","*ENDDO","*CFCLOS","FINISH"]
    return "\n".join(lines+["/EXIT,NOSAVE"])+"\n"


def structured_hex_connectivity(coords:np.ndarray)->np.ndarray:
    xs=np.unique(np.round(coords[:,0],12)); ys=np.unique(np.round(coords[:,1],12)); zs=np.unique(np.round(coords[:,2],12))
    lookup={tuple(np.round(x,12)):i for i,x in enumerate(coords)}
    conn=[]
    for ix in range(len(xs)-1):
        for iy in range(len(ys)-1):
            for iz in range(len(zs)-1):
                pts=[(xs[ix],ys[iy],zs[iz]),(xs[ix+1],ys[iy],zs[iz]),(xs[ix+1],ys[iy+1],zs[iz]),(xs[ix],ys[iy+1],zs[iz]),(xs[ix],ys[iy],zs[iz+1]),(xs[ix+1],ys[iy],zs[iz+1]),(xs[ix+1],ys[iy+1],zs[iz+1]),(xs[ix],ys[iy+1],zs[iz+1])]
                conn.append([lookup[tuple(p)] for p in pts])
    return np.asarray(conn,dtype=np.int64)


def main()->int:
    out,_=ensure_dirs(CASE); raw=out/"parametric_fields.csv"; npz=out/"acoustics_frequency_dataset.npz"; meta=out/"acoustics_frequency_dataset.json"
    for p in (raw,npz,meta): p.unlink(missing_ok=True)
    evidence=run_apdl(CASE,build_apdl(raw),timeout=420)
    rows=[r for r in read_numeric_rows(raw,["case_id","sound_speed_m_s","frequency_hz","node_id","x_m","y_m","z_m","pressure_real_pa","pressure_imag_pa"]) if r["case_id"]>=0]
    grouped=[]
    for idx,(c,f) in enumerate(PARAMETERS):
        group=sorted([r for r in rows if int(r["case_id"])==idx],key=lambda r:int(r["node_id"]))
        if not group: raise RuntimeError(f"Missing field for case {idx}")
        grouped.append(group)
    node_ids=[int(r["node_id"]) for r in grouped[0]]
    if any([int(r["node_id"]) for r in g]!=node_ids for g in grouped): raise RuntimeError("Node ordering changed between cases")
    coords=np.asarray([[r["x_m"],r["y_m"],r["z_m"]] for r in grouped[0]],float)
    conn=structured_hex_connectivity(coords)
    preal=np.asarray([[r["pressure_real_pa"] for r in g] for g in grouped],float); pimag=np.asarray([[r["pressure_imag_pa"] for r in g] for g in grouped],float)
    cases=[]
    for idx,((c,f),g) in enumerate(zip(PARAMETERS,grouped)):
        amp=np.hypot(preal[idx],pimag[idx]); probe=amp[np.argmax(coords[:,0])]
        cases.append({"case_id":idx,"geometry":{"length_m":LENGTH,"width_m":WIDTH},"frequency_hz":f,"sound_speed_m_s":c,"density_kg_m3":AIR_DENSITY,"boundary":{"x0_pressure_pa":1.0,"xL":"rigid"},"global_responses":{"maximum_pressure_pa":float(amp.max()),"maximum_spl_db":float(20*math.log10(max(amp.max(),1e-30)/REFERENCE_PRESSURE_PA)),"closed_end_transfer_amplitude":float(probe),"quarter_wave_resonance_hz":c/(4*LENGTH)}})
    metadata={"dataset_name":"MAPDL 261 parametric standing-wave acoustic fields","case_count":len(cases),"shared_mesh":True,"element":"FLUID30 KEYOPT(2)=1","analysis_type":"full harmonic acoustics","parameters":["frequency_hz","sound_speed_m_s","density_kg_m3","length_m","width_m"],"fields":["pressure_real","pressure_imag","pressure_amplitude","pressure_phase"],"cases":cases,"solver_evidence":evidence["solver_output"],"connectivity_note":"Zero-based 8-node hexahedral connectivity reconstructed from the actual mapped solver node coordinates; topology matches the FLUID30 mapped grid."}
    export_frequency_domain(npz,meta,coordinates=coords,connectivity=conn,frequencies_hz=np.asarray([f for _,f in PARAMETERS]),pressure_real=preal,pressure_imag=pimag,metadata=metadata)
    payload={"case":"I","title":"Parametric acoustic field dataset","status":"PASS","solver":"Ansys MAPDL 261","case_count":len(cases),"mesh":{"nodes":len(coords),"elements":len(conn),"connectivity":"8-node hex, zero-based"},"field_shape":list(preal.shape),"files":[str(raw.resolve()),str(npz.resolve()),str(meta.resolve()),evidence["solver_output"]]}
    write_json(out/"case_i_results.json",payload); print(payload); return 0


if __name__=="__main__": raise SystemExit(main())
