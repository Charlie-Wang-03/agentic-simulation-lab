"""NPZ export contract for distinct fluid, solid, and coupling-interface meshes."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import numpy as np

def write_multiphysics_case(path:Path,*,fluid:dict[str,np.ndarray],solid:dict[str,np.ndarray],interface:dict[str,np.ndarray],parameters:dict[str,float],units:dict[str,str],solver_metadata:dict[str,Any],time:float|None=None)->dict[str,Any]:
    arrays={}
    for prefix,domain in (("fluid",fluid),("solid",solid),("interface",interface)):
        for name,value in domain.items():arrays[f"{prefix}_{name}"]=np.asarray(value)
    if time is not None:arrays["time"]=np.asarray(time,dtype=float)
    meta={"parameters":parameters,"units":units,"solver_metadata":solver_metadata,"mesh_contract":"fluid, solid, and interface arrays are independently indexed; never row-aligned across domains"}
    arrays["metadata_json"]=np.asarray(json.dumps(meta,ensure_ascii=False));path.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,**arrays)
    return validate_multiphysics_case(path)

def validate_multiphysics_case(path:Path)->dict[str,Any]:
    required=["fluid_coordinates","fluid_connectivity","solid_coordinates","solid_connectivity","interface_coordinates","metadata_json"]
    with np.load(path,allow_pickle=False) as d:
        missing=[k for k in required if k not in d];finite={k:bool(np.isfinite(d[k]).all()) for k in d.files if d[k].dtype.kind in "fci"};shapes={k:list(d[k].shape) for k in d.files if k!="metadata_json"}
        try:meta=json.loads(str(d["metadata_json"]));metadata_ok=all(k in meta for k in ("parameters","units","solver_metadata","mesh_contract"))
        except Exception:meta={};metadata_ok=False
        independent=not (d["fluid_coordinates"].shape==d["solid_coordinates"].shape and np.array_equal(d["fluid_coordinates"],d["solid_coordinates"])) if not missing else False
    return {"path":str(path.resolve()),"missing":missing,"shapes":shapes,"all_finite":all(finite.values()),"metadata_valid":metadata_ok,"independent_domain_meshes":independent,"valid":not missing and all(finite.values()) and metadata_ok and independent}
