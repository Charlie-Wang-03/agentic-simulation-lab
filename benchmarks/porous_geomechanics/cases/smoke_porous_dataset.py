"""Case J: generate ten native MAPDL poromechanics cases for ROM/Neural Operators."""

from __future__ import annotations

import csv
import json

import numpy as np

from porous_field_export import export_mapdl_transient
from porous_geomechanics_common import *

CASE="porous_dataset";H=10.;W=1.;NU=0.;NY=10;TF=.02;NSUB=40
PARAMETERS=[
    {"K":6.5e-3,"E":4.8e5,"load":8.0,"porosity":.30},
    {"K":7.2e-3,"E":5.2e5,"load":9.0,"porosity":.32},
    {"K":7.8e-3,"E":5.5e5,"load":10.0,"porosity":.34},
    {"K":8.2e-3,"E":5.8e5,"load":11.0,"porosity":.36},
    {"K":8.6e-3,"E":6.1e5,"load":12.0,"porosity":.38},
    {"K":9.0e-3,"E":6.4e5,"load":8.5,"porosity":.40},
    {"K":9.5e-3,"E":6.8e5,"load":9.5,"porosity":.42},
    {"K":1.0e-2,"E":7.2e5,"load":10.5,"porosity":.35},
    {"K":1.05e-2,"E":7.6e5,"load":11.5,"porosity":.37},
    {"K":1.1e-2,"E":8.0e5,"load":12.5,"porosity":.39},
]

def read_rows(path):
    rows=[]
    with path.open(encoding="utf-8",errors="replace") as f:
        for r in csv.reader(f):
            if len(r)<7:continue
            try:v=list(map(float,r[:7]));rows.append(dict(zip(("time","node","x","depth","p","uy","sy"),v)))
            except ValueError:pass
    if not rows:raise RuntimeError(f"No dataset rows in {path}")
    return rows

def apdl_text(raw,par):
    return f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,CPT212
KEYOPT,1,12,1
KEYOPT,1,3,2
RECTNG,0,{W},-{H},0
LESIZE,4,,,{NY}
LESIZE,3,,,1
MSHKEY,1
AMESH,ALL
MP,EX,1,{par['E']}
MP,NUXY,1,{NU}
TB,PM,1,,,PERM
TBDATA,1,{par['K']},{par['K']},{par['K']}
TB,PM,1,,,BIOT
TBDATA,1,1.0
TB,PM,1,,,FP
TBDATA,1,2.2E9,9810,{par['porosity']}
D,ALL,UX,0
NSEL,S,LOC,Y,-{H}
D,ALL,UY,0
ALLSEL
NSEL,S,LOC,Y,0
D,ALL,PRES,0
ALLSEL
FINISH
/SOLU
ANTYPE,STATIC
NROPT,UNSYM
TIME,{TF}
NSEL,S,LOC,Y,0
SF,ALL,PRES,{par['load']}
ALLSEL
NSUBST,{NSUB},{NSUB},{NSUB}
KBC,1
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
*CFOPEN,'{ap(raw)}','csv'
*DO,II,1,{NSUB}
SET,1,II
*GET,TT,ACTIVE,0,SET,TIME
*DO,JJ,0,{NY}
DD={H}*JJ/{NY}
*DO,KK,0,1
XX={W}*KK
NN=NODE(XX,-DD,0)
*GET,PP,NODE,NN,PRES
*GET,UYV,NODE,NN,U,Y
*GET,SYV,NODE,NN,S,Y
*VWRITE,TT,NN,XX,DD,PP,UYV,SYV
(E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
*ENDDO
*ENDDO
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""

def main()->int:
    p=clean_case(CASE);cases=[];blocked=None
    for index,par in enumerate(PARAMETERS):
        name=f"dataset_{index:03d}";cp=clean_case(name);raw=cp["dir"] / "fields_raw.csv";run=run_apdl(name,apdl_text(raw,par),timeout=240)
        try:
            if run["exit_code"]!=0:raise RuntimeError("MAPDL nonzero exit; "+" ".join(line.strip() for line in run["listing"].splitlines() if "LICENSE" in line.upper())[:500])
            errs=[line.strip() for line in run["listing"].splitlines() if "*** ERROR ***" in line]
            if errs:raise RuntimeError(str(errs[:5]))
            rows=read_rows(raw);times=sorted({r["time"] for r in rows});nodes=sorted({int(r["node"]) for r in rows});by={(r["time"],int(r["node"])):r for r in rows};coords=np.asarray([[by[(times[-1],n)]["x"],-by[(times[-1],n)]["depth"]] for n in nodes]);pressure=np.asarray([[by[(t,n)]["p"] for n in nodes] for t in times]);uy=np.asarray([[by[(t,n)]["uy"] for n in nodes] for t in times]);sy=np.asarray([[by[(t,n)]["sy"] for n in nodes] for t in times]);order=np.lexsort((coords[:,0],-coords[:,1]));coords=coords[order];pressure=pressure[:,order];uy=uy[:,order];sy=sy[:,order];disp=np.zeros((len(times),len(nodes),2));disp[:,:,1]=uy;stress=np.zeros((len(times),len(nodes),3));stress[:,:,1]=sy;eff=stress.copy();eff[:,:,1]=sy+pressure;conn=np.asarray([[2*j,2*j+1,2*j+3,2*j+2] for j in range(NY)])
            top=np.where(np.isclose(coords[:,1],0))[0];settlement=np.abs(np.mean(disp[:,top,1],axis=1));sinf=par["load"]*H/par["E"];degree=settlement/sinf;meta={"case":"J","case_id":index,"solver":"MAPDL 261 CPT212","model":"saturated Biot consolidation","parameters":{"permeability_m_s":par["K"],"porosity":par["porosity"],"E_pa":par["E"],"nu":NU,"fluid_bulk_modulus_pa":2.2e9,"fluid_viscosity":"implicit in hydraulic conductivity","load_pa":par["load"],"drainage":"top single drainage","geometry":{"height_m":H,"width_m":W}},"units":{"coordinates":"m","time":"s","pore_pressure":"Pa","displacement":"m","stress":"Pa"},"global_responses":{"settlement_m":settlement.tolist(),"degree_of_consolidation":degree.tolist(),"maximum_pore_pressure_pa":float(pressure.max()),"drainage_flow":"not directly exported; pressure/settlement histories retained"}}
            npz=export_mapdl_transient(cp["dir"] / "poromechanics_case.npz",coordinates=coords,connectivity=conn,time=times,pore_pressure=pressure,displacement=disp,stress=stress,effective_stress=eff,metadata=meta);cases.append({"case_id":index,"status":"PASS","parameters":par,"npz":str(npz.resolve()),"result":str(cp["result"].resolve())});write_json(cp["result"],status_payload("J",f"Poromechanics dataset case {index}","PASS",metadata=meta,files=[str(x.resolve()) for x in (cp["input"],cp["solver"],raw,npz)]))
        except Exception as exc:
            status,error=classify_solver_error(exc);blocked={"case_id":index,"status":status,"error":error,"solver_output":str(cp["solver"].resolve())};write_json(cp["result"],status_payload("J",f"Poromechanics dataset case {index}",status,error=error));break
    status="PASS" if len(cases)==len(PARAMETERS) else (blocked or {}).get("status","FAIL");payload=status_payload("J","Parameterized poromechanics transient dataset",status,requested_cases=len(PARAMETERS),completed_cases=len(cases),cases=cases,blocked=blocked,organization={"field_shape":"[time,node] (displacement [time,node,component])","format":"compressed NPZ + JSON metadata","common_time":{"final_s":TF,"samples":NSUB}},files=[c["npz"] for c in cases]);write_json(p["result"],payload);print(json.dumps(payload,indent=2));return 0 if status in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
