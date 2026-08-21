"""Case A: steady one-dimensional conduction through a rectangular solid."""

from __future__ import annotations

import math

from thermal_smoke_common import *

CASE = "thermal_conduction"
L, W, H = 0.10, 0.02, 0.02
K, TCOLD, THOT, ESIZE = 15.0, 20.0, 120.0, 0.01


def main() -> int:
    clean_case(CASE)
    raw, summary = OUT / f"{CASE}_raw.csv", OUT / f"{CASE}_summary.csv"
    profile, chart, result_file = OUT / f"{CASE}_profile.csv", OUT / f"{CASE}_temperature.svg", OUT / f"{CASE}_results.json"
    apdl = f"""/BATCH
/CLEAR,START
/PREP7
/UNITS,SI
ET,1,SOLID70
MP,KXX,1,{K}
BLOCK,0,{L},0,{W},0,{H}
ESIZE,{ESIZE}
MSHKEY,1
TYPE,1
MAT,1
VMESH,ALL
NSEL,S,LOC,X,0
D,ALL,TEMP,{THOT}
NSEL,S,LOC,X,{L}
D,ALL,TEMP,{TCOLD}
ALLSEL,ALL
/SOLU
ANTYPE,STATIC
SOLVE
FINISH
/POST1
SET,LAST
{apdl_sum_reaction(0.0)}
*GET,NNODES,NODE,0,COUNT
*GET,NELEMS,ELEM,0,COUNT
{apdl_export_nodes(raw)}
*CFOPEN,'{apdl_path(summary.with_suffix(''))}','csv'
*VWRITE,NNODES,NELEMS,QREACTION
(F12.0,',',F12.0,',',E22.14)
*CFCLOS
FINISH
/EXIT,NOSAVE
"""
    inp, solver_out = run_apdl(CASE, apdl)
    nodes = numeric_rows(raw, ["node_id", "x_m", "temperature_c"])
    curve = average_by_x(nodes)
    write_csv(profile, curve)
    stats = scalar_row(summary, ["node_count", "element_count", "hot_end_reaction_w"])
    area = W * H
    theory_q = K * area * (THOT - TCOLD) / L
    theory = [{"x_m": r["x_m"], "temperature_c": THOT + (TCOLD-THOT)*r["x_m"]/L} for r in curve]
    max_temp_error = max(abs(a["temperature_c"]-b["temperature_c"]) for a,b in zip(curve,theory))
    q_ansys = abs(stats["hot_end_reaction_w"])
    flux_ansys = q_ansys / area
    errors = {"heat_flow_relative": rel_error(q_ansys, theory_q), "max_temperature_absolute_c": max_temp_error}
    checks = {"solver_output_exists": solver_out.is_file(), "temperature_is_linear": max_temp_error < 0.05,
              "heat_flow_error_below_1pct": errors["heat_flow_relative"] < 0.01,
              "boundary_extrema_match": abs(max(r["temperature_c"] for r in nodes)-THOT)<0.02 and abs(min(r["temperature_c"] for r in nodes)-TCOLD)<0.02}
    svg_plot(chart, [([r["x_m"] for r in curve],[r["temperature_c"] for r in curve],"Ansys"),
                     ([r["x_m"] for r in theory],[r["temperature_c"] for r in theory],"Fourier")],
             "Case A: 1D steady conduction", "x [m]", "Temperature [C]")
    files=[inp,solver_out,raw,profile,chart,result_file]
    payload=result_payload("A", "Steady-State Thermal", {"length_m":L,"width_m":W,"height_m":H,"conductivity_w_mk":K,"hot_c":THOT,"cold_c":TCOLD},
        {"nodes":int(stats["node_count"]),"elements":int(stats["element_count"])},
        {"min_temperature_c":min(r["temperature_c"] for r in nodes),"max_temperature_c":max(r["temperature_c"] for r in nodes),"heat_flow_w":q_ansys,"heat_flux_w_m2":flux_ansys},
        {"heat_flow_w":theory_q,"heat_flux_w_m2":theory_q/area},errors,checks,files)
    write_json(result_file,payload)
    print(f"Case A {payload['status']}: Q={q_ansys:.9g} W, theory={theory_q:.9g} W, error={100*errors['heat_flow_relative']:.4g}%")
    return 0 if payload["status"]=="PASS" else 1

if __name__ == "__main__": raise SystemExit(main())
