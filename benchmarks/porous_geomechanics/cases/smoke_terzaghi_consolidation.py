"""Case F: native CPT212 one-dimensional Terzaghi consolidation benchmark."""

from __future__ import annotations

import csv
import math

import numpy as np

from porous_field_export import export_mapdl_transient
from porous_geomechanics_common import *

CASE="terzaghi_consolidation";H=10.;W=1.;E=5.8e5;NU=0.;K=8.62e-3;LOAD=10.;NY=20;FINAL_TIME=.02;NSUB=100

def analytical_u_ratio(depth:float,tv:float,terms:int=200)->float:
    return 4/math.pi*sum(math.sin((2*m+1)*math.pi*depth/(2*H))/(2*m+1)*math.exp(-((2*m+1)**2)*math.pi**2*tv/4) for m in range(terms))

def analytical_degree(tv:float,terms:int=200)->float:
    remaining=8/math.pi**2*sum(math.exp(-((2*m+1)**2)*math.pi**2*tv/4)/(2*m+1)**2 for m in range(terms));return 1-remaining

def read_raw(path):
    out=[]
    with path.open(encoding="utf-8",errors="replace") as f:
        for row in csv.reader(f):
            if len(row)<7:continue
            try:out.append(dict(zip(("time_s","node","x_m","depth_m","pore_pressure_pa","uy_m","stress_y_pa"),map(float,row[:7]))))
            except ValueError:pass
    if not out:raise RuntimeError(f"No numeric Terzaghi rows in {path}")
    return out

def main()->int:
    p=clean_case(CASE);raw=p["dir"] / "terzaghi_raw.csv"
    apdl=f"""/BATCH
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
MP,EX,1,{E}
MP,NUXY,1,{NU}
TB,PM,1,,,PERM
TBDATA,1,{K},{K},{K}
TB,PM,1,,,BIOT
TBDATA,1,1.0
ALLSEL
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
TIME,{FINAL_TIME}
NSEL,S,LOC,Y,0
SF,ALL,PRES,{LOAD}
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
YY=-{H}*JJ/{NY}
*DO,KK,0,1
XX={W}*KK
NN=NODE(XX,YY,0)
*GET,PP,NODE,NN,PRES
*GET,UYV,NODE,NN,U,Y
*GET,SYV,NODE,NN,S,Y
DD=-YY
*VWRITE,TT,NN,XX,DD,PP,UYV,SYV
(E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14,',',E22.14)
*ENDDO
*ENDDO
*ENDDO
*CFCLOS
/EXIT,NOSAVE
"""
    run=run_apdl(CASE,apdl,timeout=300)
    try:
        if run["exit_code"]!=0:raise RuntimeError("MAPDL nonzero exit; "+" ".join(line.strip() for line in run["listing"].splitlines() if "LICENSE" in line.upper())[:500])
        errs=[line.strip() for line in run["listing"].splitlines() if "*** ERROR ***" in line]
        if errs:raise RuntimeError("MAPDL errors: "+str(errs[:5]))
        rows=read_raw(raw);times=sorted({r["time_s"] for r in rows});nodes=sorted({int(r["node"]) for r in rows});by={(r["time_s"],int(r["node"])):r for r in rows}
        coords=np.asarray([[by[(times[-1],n)]["x_m"],-by[(times[-1],n)]["depth_m"]] for n in nodes]);pressure=np.asarray([[by[(t,n)]["pore_pressure_pa"] for n in nodes] for t in times]);uy=np.asarray([[by[(t,n)]["uy_m"] for n in nodes] for t in times]);sy=np.asarray([[by[(t,n)]["stress_y_pa"] for n in nodes] for t in times]);disp=np.zeros((len(times),len(nodes),2));disp[:,:,1]=uy
        # Sort logical nodes by depth then x for a deterministic quad connectivity map.
        order=np.lexsort((coords[:,0],-coords[:,1]));coords=coords[order];pressure=pressure[:,order];disp=disp[:,order];sy=sy[:,order]
        conn=np.asarray([[2*j,2*j+1,2*j+3,2*j+2] for j in range(NY)],dtype=int);stress=np.zeros((len(times),len(nodes),3));stress[:,:,1]=sy;effective=stress.copy();effective[:,:,1]=sy+pressure
        cv=K*E;sample_tvs=[.05,.1,.2,.5,1.0];comparisons=[]
        top_ids=np.where(np.isclose(coords[:,1],0))[0];settlement=np.mean(disp[:,top_ids,1],axis=1);sfinal=LOAD*H/E
        for tv in sample_tvs:
            target=tv*H*H/cv;i=int(np.argmin(np.abs(np.asarray(times)-target)));depths=-coords[:,1];theory=np.asarray([LOAD*analytical_u_ratio(float(d),tv) for d in depths]);p_err=float(np.linalg.norm(pressure[i]-theory)/max(np.linalg.norm(theory),1e-30));u_theory=analytical_degree(tv);u_num=float(abs(settlement[i])/sfinal);comparisons.append({"Tv":tv,"time_s":times[i],"pore_profile_l2_relative":p_err,"degree_numerical":u_num,"degree_theory":u_theory,"degree_absolute_error":abs(u_num-u_theory)})
        checks={"native_pore_pressure_positive":float(pressure.max())>LOAD*.5,"pore_pressure_dissipates":float(np.mean(abs(pressure[-1])))<float(np.mean(abs(pressure[0]))),"profile_l2_max_lt_12pct":max(x["pore_profile_l2_relative"] for x in comparisons)<.12,"degree_error_max_lt_8pct":max(x["degree_absolute_error"] for x in comparisons)<.08,"settlement_grows":abs(settlement[-1])>abs(settlement[0]),"final_settlement_within_8pct":relative_error(abs(settlement[-1]),sfinal)<.08}
        npz=export_mapdl_transient(p["dir"] / "terzaghi_field.npz",coordinates=coords,connectivity=conn,time=times,pore_pressure=pressure,displacement=disp,stress=stress,effective_stress=effective,metadata={"case":"F","solver":"MAPDL 261 CPT212","model":"saturated Biot consolidation","parameters":{"E_pa":E,"nu":NU,"permeability_m_s":K,"Biot":1.,"load_pa":LOAD},"units":{"coordinates":"m","time":"s","pore_pressure":"Pa","displacement":"m","stress":"Pa"}})
        payload=status_payload("F","Terzaghi one-dimensional consolidation","PASS" if all(checks.values()) else "FAIL",solver="Ansys MAPDL",analysis_type="CPT212 structural-pore-fluid diffusion; ANTYPE,STATIC with physical time",material_model="saturated Biot porous medium",permeability_m_s=K,porosity="not required by incompressible VM264 formulation",mesh={"element":"CPT212","elements":NY,"nodes":len(nodes)},time={"final_s":FINAL_TIME,"substeps":NSUB},results={"initial_mean_pressure_pa":float(np.mean(pressure[0])),"final_mean_pressure_pa":float(np.mean(pressure[-1])),"final_settlement_m":float(abs(settlement[-1])),"comparisons":comparisons},theory={"Terzaghi_series":"single drainage Fourier series","cv_m2_s":cv,"final_settlement_m":sfinal},errors={"maximum_profile_l2_relative":max(x["pore_profile_l2_relative"] for x in comparisons),"maximum_degree_absolute":max(x["degree_absolute_error"] for x in comparisons)},checks=checks,files=[str(x.resolve()) for x in (p["input"],p["solver"],p["log"],raw,npz)])
    except Exception as exc:
        status,error=classify_solver_error(exc);payload=status_payload("F","Terzaghi one-dimensional consolidation",status,error=error,solver_output=str(p["solver"].resolve()))
    write_json(p["result"],payload);print(payload);return 0 if payload["status"] in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
