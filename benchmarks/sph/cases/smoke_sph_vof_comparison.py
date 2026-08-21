"""Case K: dimensionless cross-check of geometrically similar SPH and Fluent VOF dam breaks."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from free_surface_sph_common import ROOT, OUTPUT_ROOT, GRAVITY


OUT=OUTPUT_ROOT/"case_k_vof_comparison"; OUT.mkdir(parents=True,exist_ok=True)
sph_path=OUTPUT_ROOT/"case_b_dam_break"/"result.json"; vof_json_path=ROOT/"outputs"/"fluent_vof.json"; vof_csv_path=ROOT/"outputs"/"fluent_vof_front.csv"
payload={"case":"K","status":"FAIL"}
try:
    sph=json.loads(sph_path.read_text(encoding="utf-8")); vof=json.loads(vof_json_path.read_text(encoding="utf-8"))
    with vof_csv_path.open(newline="",encoding="utf-8-sig") as stream: vof_rows=list(csv.DictReader(stream))
    # Geometry is exactly 1:10 similar. Compare x/L and t*sqrt(g/H), which
    # preserves gravity-driven free-surface dynamics under geometric scaling.
    sph_series=[{"tau":x["time_s"]*math.sqrt(GRAVITY/0.10),"front_over_l":(x["front_x_m"]+0.15)/0.30} for x in sph["history"]]
    vof_series=[{"tau":float(x["time_s"])*math.sqrt(GRAVITY/1.0),"front_over_l":float(x["front_x_m"])/3.0} for x in vof_rows]
    comparisons=[]
    for s in sph_series:
        v=min(vof_series,key=lambda x:abs(x["tau"]-s["tau"]))
        if abs(v["tau"]-s["tau"])<=0.20:
            comparisons.append({"tau":s["tau"],"sph_front_over_l":s["front_over_l"],"vof_front_over_l":v["front_over_l"],"difference":s["front_over_l"]-v["front_over_l"]})
    rmse=math.sqrt(sum(x["difference"]**2 for x in comparisons)/len(comparisons)) if comparisons else math.inf
    checks={"sph_pass":sph.get("status")=="PASS","vof_pass":vof.get("status")=="PASS","five_comparison_points":len(comparisons)>=5,"dimensionless_front_rmse_lt_0p25":rmse<0.25,"sph_mass_drift_lt_1pct":sph.get("relative_mass_drift",1.0)<0.01,"vof_volume_drift_lt_8pct":vof["results"]["relative_alpha_drift"]<0.08}
    payload.update({"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"geometry_relation":"SPH dimensions are exactly 1:10 of Fluent VOF dimensions","methods":{"sph":"Lagrangian IISPH","vof":"Eulerian Fluent VOF"},"dimensionless_front_rmse":rmse,"comparisons":comparisons,"sph_mass_drift":sph.get("relative_mass_drift"),"vof_volume_fraction_drift":vof["results"]["relative_alpha_drift"],"comparison_scope":{"quantitative":["dimensionless front position","global mass/volume conservation"],"field_artifacts_available":["SPH particle pressure/free surface","Fluent pressure/volume-fraction snapshots"],"not_claimed":"The archived Fluent result does not retain matching wall-pressure probes or solver runtime, so no numerical wall-pressure or runtime agreement is claimed."},"sph_source":str(sph_path),"vof_source":str(vof_json_path)})
except Exception as exc:
    payload["error"]=f"{type(exc).__name__}: {exc}"
(OUT/"result.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
report=["# SPH vs Fluent VOF comparison","",f"Status: **{payload['status']}**","","The two real Ansys solutions use exactly similar 1:10 geometry. Front propagation is compared with gravity-scaled time and tank-normalized distance; pointwise agreement is not required.","",f"Dimensionless front RMSE: `{payload.get('dimensionless_front_rmse')}`",f"SPH mass drift: `{payload.get('sph_mass_drift')}`",f"VOF volume-fraction drift: `{payload.get('vof_volume_fraction_drift')}`","","Raw SPH pressure/free-surface fields and Fluent pressure/volume-fraction snapshots are retained. The archived Fluent result has no matching wall-pressure probe or solver-runtime record, so this report does not claim numerical wall-pressure or runtime agreement.","","## Checks","",*(f"- {k}: {v}" for k,v in payload.get("checks",{}).items())]
(ROOT/"SPH_VOF_COMPARISON.md").write_text("\n".join(report)+"\n",encoding="utf-8")
print(json.dumps(payload,indent=2))
