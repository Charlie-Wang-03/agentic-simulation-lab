"""Case K: coarse/medium/fine mesh sensitivity for backward-facing step."""
from __future__ import annotations
import json,math
from fluent_smoke_common import OUT,base_payload,svg_xy_plot,write_csv,write_json
from smoke_fluent_backward_step import solve_bfs

CASE="fluent_mesh_sensitivity"
def main()->int:
    payload=base_payload(CASE,"Case K: backward-facing-step mesh sensitivity")
    try:
        coarse=solve_bfs("coarse",20,90,20,10)
        medj=json.loads((OUT/"fluent_backward_step.json").read_text(encoding="utf-8"))
        medium={"tag":"medium","stats":medj["mesh"],"reattachment_h":medj["results"]["reattachment_length_h"],"mass_error":medj["results"]["mass_imbalance_relative"],"npz_check":{"valid":True},"files":[]}
        fine=solve_bfs("fine",60,270,60,30)
        rr=[coarse,medium,fine]
        table=[{"mesh":r["tag"],"cells":r["stats"]["cells"],"nodes":r["stats"]["nodes"],"reattachment_length_h":r["reattachment_h"],"mass_imbalance_relative":r["mass_error"]} for r in rr]
        delta_cm=abs(table[1]["reattachment_length_h"]-table[0]["reattachment_length_h"])/table[1]["reattachment_length_h"]
        delta_mf=abs(table[2]["reattachment_length_h"]-table[1]["reattachment_length_h"])/table[2]["reattachment_length_h"]
        csvp=write_csv(OUT/f"{CASE}.csv",list(table[0]),table); svg=svg_xy_plot(OUT/f"{CASE}.svg",[(x["cells"],x["reattachment_length_h"]) for x in table],title="Case K: mesh sensitivity",xlabel="cell count",ylabel="reattachment length x_r/h")
        checks={"cell_counts_increase":table[0]["cells"]<table[1]["cells"]<table[2]["cells"],"all_reattachment_detected":all(x["reattachment_length_h"] for x in table),"medium_fine_change_lt_8pct":delta_mf<.08,"all_mass_errors_lt_2pct":all(x["mass_imbalance_relative"]<.02 for x in table),"coarse_and_fine_fields_valid":coarse["npz_check"]["valid"] and fine["npz_check"]["valid"]}
        payload.update({"selected_model":"Case I backward-facing step, Re_h=200","results":table,"relative_changes":{"coarse_to_medium":delta_cm,"medium_to_fine":delta_mf},"checks":checks,"status":"PASS" if all(checks.values()) else "FAIL","files":[str(x.resolve()) for x in [csvp,svg,*coarse["files"],*fine["files"]]]})
    except Exception as exc: payload.update({"status":"FAIL","error":f"{type(exc).__name__}: {exc}"})
    write_json(OUT/f"{CASE}.json",payload); print(payload); return 0 if payload["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
