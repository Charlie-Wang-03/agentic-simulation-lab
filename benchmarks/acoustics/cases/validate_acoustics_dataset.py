"""Independent validation for the acoustic NPZ dataset and transient evidence."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from acoustics_common import ACOUSTICS_OUT, ensure_dirs, read_numeric_rows, write_json


def main()->int:
    out,_=ensure_dirs("case_i_dataset")
    npz_path=out/"acoustics_frequency_dataset.npz"; meta_path=out/"acoustics_frequency_dataset.json"
    errors=[]
    if not npz_path.is_file(): errors.append(f"missing {npz_path}")
    if not meta_path.is_file(): errors.append(f"missing {meta_path}")
    if errors:
        result={"status":"FAIL","errors":errors}; write_json(out/"validation_results.json",result); print(result); return 1
    meta=json.loads(meta_path.read_text(encoding="utf-8"))
    with np.load(npz_path,allow_pickle=False) as d:
        required={"coordinates","connectivity","frequency","pressure_real","pressure_imag","pressure_amplitude","pressure_phase"}
        missing=required-set(d.files)
        if missing: errors.append(f"missing arrays {sorted(missing)}")
        coords=d["coordinates"]; conn=d["connectivity"]; freq=d["frequency"]; pr=d["pressure_real"]; pi=d["pressure_imag"]; pa=d["pressure_amplitude"]; pp=d["pressure_phase"]
        checks={
            "case_count_10_to_20":10<=len(freq)<=20,
            "coordinates_shape":coords.ndim==2 and coords.shape[1]==3 and len(coords)>0,
            "connectivity_shape":conn.ndim==2 and conn.shape[1]==8 and len(conn)>0,
            "connectivity_in_bounds":int(conn.min())>=0 and int(conn.max())<len(coords),
            "complex_field_shapes":pr.shape==pi.shape==pa.shape==pp.shape==(len(freq),len(coords)),
            "finite_arrays":all(np.isfinite(x).all() for x in (coords,freq,pr,pi,pa,pp)),
            "amplitude_consistency":bool(np.allclose(pa,np.hypot(pr,pi),rtol=1e-10,atol=1e-12)),
            "phase_consistency":bool(np.allclose(pp,np.arctan2(pi,pr),rtol=1e-10,atol=1e-12)),
            "nonzero_pressure":bool(np.max(pa)>0),
            "metadata_case_count":meta.get("case_count")==len(freq) and len(meta.get("cases",[]))==len(freq),
            "units_complete":meta.get("units",{}).get("pressure")=="Pa" and meta.get("units",{}).get("frequency")=="Hz",
            "parameters_complete":all(all(k in c for k in ("case_id","frequency_hz","sound_speed_m_s","density_kg_m3","geometry","boundary","global_responses")) for c in meta.get("cases",[])),
        }
    transient=ACOUSTICS_OUT/"case_d_transient"/"probe_history.csv"
    trows=read_numeric_rows(transient,["time_s","p1","p2","p3"]) if transient.is_file() else []
    checks["transient_time_ordering_evidence"]=len(trows)>2 and all(trows[i+1]["time_s"]>trows[i]["time_s"] for i in range(len(trows)-1))
    checks["metadata_fields_declared"]=set(("pressure_real","pressure_imag","pressure_amplitude","pressure_phase")).issubset(meta.get("fields",[]))
    errors += [name for name,value in checks.items() if not value]
    result={"status":"PASS" if not errors else "FAIL","case_count":len(freq),"checks":checks,"errors":errors,"reloaded_npz":str(npz_path.resolve()),"metadata":str(meta_path.resolve()),"transient_evidence":str(transient.resolve())}
    write_json(out/"validation_results.json",result); print(json.dumps(result,indent=2)); return 0 if result["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
