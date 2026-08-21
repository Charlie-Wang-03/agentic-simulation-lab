"""Independent full-reload validation for phase/reactive NPZ datasets."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from phase_reactive_common import DATA, OUT, write_json


def validate_phase(path:Path)->dict:
    errors=[]
    with np.load(path,allow_pickle=False) as d:
        req=("coordinates","connectivity","time","temperature","liquid_fraction","interface_position","total_liquid_fraction","energy_balance_relative_error","metadata_json")
        errors += [f"missing {x}" for x in req if x not in d]
        if errors:return {"status":"FAIL","errors":errors}
        f=d["liquid_fraction"];t=d["temperature"];time=d["time"];meta=json.loads(str(d["metadata_json"]))
        checks={"finite":bool(np.isfinite(t).all() and np.isfinite(f).all()),"fraction_bounded":bool(((f>=0)&(f<=1)).all()),
          "time_ordering":bool(np.all(np.diff(time)>0)),"melt_fraction_trend":bool(np.all(np.diff(d["total_liquid_fraction"],axis=1)>=-1e-12)),
          "energy_balance_finite_lt_15pct":bool(np.isfinite(d["energy_balance_relative_error"]).all() and np.max(d["energy_balance_relative_error"])<0.15),
          "metadata_complete":all(k in meta for k in ("units","inputs","fields","solver_version","model_settings")),"case_count_12":t.shape[0]==12}
    return {"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"errors":errors}


def validate_reactive(path:Path)->dict:
    errors=[]
    with np.load(path,allow_pickle=False) as d:
        meta=json.loads(str(d["metadata_json"]));names=meta.get("species_names",[]);keys=[f"species_{x}" for x in names]
        errors += [f"missing {x}" for x in keys if x not in d]
        if errors:return {"status":"FAIL","errors":errors}
        vals=[d[x] for x in keys];sums=sum(vals)
        numeric=[d[x] for x in ("coordinates","velocity_x","velocity_y","pressure","temperature","reaction_rate","heat_release_rate",*keys)]
        params=d["case_parameters"]; cp=float(meta["model_settings"]["effective_cp_J_kgK"]);q=float(meta["model_settings"]["heat_of_reaction_J_kg_fuel"])
        thermal_errors=[]
        fuel=d[keys[0]]
        for n in range(len(params)):
            expected=(params[n,2]-fuel[n])*q/cp
            thermal_errors.append(float(np.max(np.abs((d["temperature"][n]-params[n,1])-expected))))
        checks={"finite":all(bool(np.isfinite(x).all()) for x in numeric),"species_bounded":all(bool(((x>=0)&(x<=1)).all()) for x in vals),
          "species_sum_error_lt_1e-10":float(np.max(np.abs(sums-1)))<1e-10,"reaction_rate_nonnegative":bool((d["reaction_rate"]>=0).all()),
          "heat_release_temperature_identity_error_lt_1e-8K":max(thermal_errors)<1e-8,
          "metadata_complete":all(k in meta for k in ("species_names","chemical_mechanism","units","inputs","solver_version","model_settings")),
          "case_count_12":d["temperature"].shape[0]==12}
    return {"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"errors":errors}


def main()->int:
    result={"phase_change":validate_phase(DATA/"phase_change"/"phase_change_dataset.npz"),
            "reactive_flow":validate_reactive(DATA/"reactive_flow"/"reactive_flow_dataset.npz")}
    result["status"]="PASS" if all(x["status"]=="PASS" for x in result.values()) else "FAIL"
    write_json(OUT/"dataset_validation.json",result);print(result);return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
