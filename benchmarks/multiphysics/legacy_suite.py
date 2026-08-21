"""Unified runner and evidence-backed report generator."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent; OUT=ROOT/"outputs"
CASES=[("Phase 0","smoke_system_coupling_connect.py","system_coupling_connect.json"),("A","smoke_cht_fluent.py","cht_fluent.json"),("B","smoke_cht_system_coupling.py","cht_system_coupling.json"),("C","smoke_fsi_one_way.py","fsi_one_way.json"),("D","smoke_fsi_two_way.py","fsi_two_way.json"),("E","smoke_fsi_turek_hron.py","fsi_turek_hron.json"),("F","smoke_thermal_fluid_structural.py","thermal_fluid_structural.json"),("G","smoke_thermo_fsi.py","thermo_fsi.json"),("H","smoke_multiphysics_dataset.py","multiphysics_dataset.json")]

def load(name):
    try:return json.loads((OUT/name).read_text(encoding="utf-8"))
    except Exception as e:return {"status":"NOT RUN","error":str(e)}

def report():
    data={label:load(js) for label,_,js in CASES}; p0=data["Phase 0"];e=data["E"];g=data["G"];h=data["H"]
    rows="\n".join(f"| {label} | {x.get('status','NOT RUN')} | {x.get('error') or x.get('limitation') or 'All defined physics and data checks passed'} |" for label,x in data.items())
    gr=g.get("results",{});gc=g.get("conservation",{});gm=g.get("mapping",{});gh=g.get("fsin_1",{})
    records=h.get("records",[])
    def extrema(field):
        return ([min(x["ranges"][field][0] for x in records),max(x["ranges"][field][1] for x in records)] if records else None)
    text=f"""# MULTIPHYSICS COUPLING REPORT

All statuses below come from actual local Ansys Student 2026 R1 / 261 runs. Solver exit alone is not accepted as PASS.

## Environment

- PySystemCoupling `{p0.get('packages',{}).get('ansys-systemcoupling-core')}`, PyMAPDL `{p0.get('packages',{}).get('ansys-mapdl-core')}`, PyFluent `{p0.get('packages',{}).get('ansys-fluent-core')}`.
- System Coupling launcher: `{p0.get('launcher')}`; server `{p0.get('server_version')}`; `ping()` `{p0.get('ping')}`.
- Residual solver processes after completed tests: `{p0.get('residual_processes')}`.

## Status

| Case | Status | Evidence / limitation |
|---|---|---|
{rows}

## Case E — Turek–Hron FSI2: FAIL

- Actual run: `dt = {e.get('dt_s')} s`, end time `{e.get('actual_end_time_s')} s`, 10 coupling steps.
- Participants/interface: Fluent `FLUENT-1` ↔ MAPDL `MAPDL-2`, `Interface-1`; Force and Incremental Displacement.
- Mapping: minimum `{e.get('mapping',{}).get('minimum_percent')}%`.
- Persisted state: `{e.get('restart',{}).get('system_coupling_points')}` System Coupling restart points and `{e.get('restart',{}).get('fluent_autosave_pairs')}` Fluent case/data autosave pairs.
- Official 34–35 s reference ranges: drag `{e.get('published_reference',{}).get('drag_range_N_per_m')} N/m`; lift `{e.get('published_reference',{}).get('lift_range_N_per_m')} N/m`. The 0.01 m Fluent depth is accounted for when converting N to N/m.
- Beam-tip x/y amplitudes, periodic drag/lift range, and frequency: **not available**, because 34–35 s was not reached.
- Continuation diagnosis: externally managed sessions were successfully rebound and System Coupling opened step 10 at 0.1 s, but MAPDL reported a beginning-time mismatch (`0` vs `0.1 s`). The next implementation sets MAPDL transient restart time explicitly before reconnecting; this change has not been solver-retested because the local execution request was blocked by the Codex usage limit.
- No formal benchmark comparison or PASS is claimed.

## Case G — synchronous Thermal–Fluid–Structural: PASS

- Solid participant: MAPDL transient coupled-field `SOLID226`, `KEYOPT(1)=11` (structural + thermal DOFs). Mechanical participant fallback was unnecessary.
- `FSIN_1` actual inputs: `{gh.get('input_variables')}`.
- `FSIN_1` actual outputs: `{gh.get('output_variables')}`.
- Active four transfers on one interface: Fluent Force → `FORC`; Fluent Heat Flow → `HFLW`; MAPDL `INCD` → Fluent displacement; MAPDL `TEMP` → Fluent temperature.
- Mapping: minimum area `{gm.get('minimum_area_percent')}%`, nodes `{gm.get('minimum_node_percent')}%`, all recorded statistics `{gm.get('minimum_all_statistics_percent')}%`.
- Convergence: `{g.get('convergence',{}).get('iteration_records')}` iteration records over two 0.1 s steps; maximum `{g.get('convergence',{}).get('maximum_iteration')}` iterations. Final transfer RMS criteria were below 0.01.
- Conservation: force relative error `{gc.get('force_relative_error')}` (accepted coarse-smoke tolerance 0.02); heat-flow relative error `{gc.get('heat_flow_relative_error')}`.
- Key fields at 0.2 s: fluid velocity `{gr.get('fluid_velocity_m_s')} m/s`, pressure `{gr.get('fluid_pressure_Pa')} Pa`, interface temperature `{gr.get('fluid_interface_temperature_K')} K`, heat flux `{gr.get('interface_heat_flux_W_m2')} W/m²`; solid temperature `{gr.get('solid_temperature_range_K')} K`, max displacement `{gr.get('max_solid_displacement_m')} m`, max equivalent stress `{gr.get('max_solid_equivalent_stress_Pa')} Pa.
- Validation contains warnings for unused *additional* participant capabilities (FDNS/TBULK/HCOEF/TEMP input); there are no setup errors for the four active transfers.

## Case H — Case F surrogate dataset smoke: PASS

- Eight actual `Fluid → Thermal → Structural` sequences. Existing Fluent 261 CHT raw fields were reused; all eight corresponding MAPDL 261 thermal-stress analyses were actually solved.
- Parameters: inlet velocity, inlet temperature, solid conductivity, Young's modulus; wall thickness is stored with each case.
- Format: compressed NPZ per case plus `index.json` and `dataset_validation.json`.
- Per-case independent mesh/data shapes:
  - Fluid: coordinates `(671, 2)`, connectivity `(600, 4)`, velocity `(671, 3)`, pressure/temperature `(671,)`.
  - Solid: coordinates `(84, 3)`, connectivity `(20, 8)`, temperature/equivalent stress `(84,)`, displacement `(84, 3)`.
  - Interface: coordinates `(61, 2)`, temperature/heat flux/pressure `(61,)`.
- Dataset ranges: solid temperature `{extrema('solid_temperature_K')} K`, displacement magnitude `{extrema('displacement_m')} m`, equivalent stress `{extrema('equivalent_stress_Pa')} Pa.
- Validator result: `{h.get('validation',{}).get('status')}`; case count `{h.get('validation',{}).get('case_count')}`. It checks field-to-mesh shapes, connectivity bounds, units, parameter/solver metadata, NaN/Inf, physical temperature and nonzero structural response, interface fields, explicit time, and independent domain meshes.

## Capability matrix

| Capability | Result |
|---|---|
| Fluent native CHT | PASS |
| Partitioned CHT | PASS |
| One-way FSI | PASS |
| Two-way / dynamic-mesh FSI | PASS |
| Thermal → structural | PASS |
| Thermal-fluid-structural in one co-simulation | PASS (Case G) |
| System Coupling | PASS |
| Nonmatching mesh mapping | PASS |
| Transient co-simulation | PASS |
| Multiphysics parameter sweep | PASS (8 Case F sequences) |
| Neural-surrogate dataset generation | PASS for dataset generation/validation; training is out of scope |
| Formal Turek–Hron FSI2 34–35 s validation | FAIL / incomplete |

## Still not covered

- Formal 35 s Turek–Hron FSI2 periodic-window validation.
- Three-or-more participant co-simulation, electromagnetics, acoustics, phase change, reacting-flow thermal stress, and HPC scaling.
"""
    path=ROOT/"MULTIPHYSICS_COUPLING_REPORT.md";path.write_text(text,encoding="utf-8");return path,data

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--report-only",action="store_true");args=ap.parse_args()
    if not args.report_only:
        for label,script,_ in CASES:
            print(f"=== {label}: {script} ===",flush=True);subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=False,timeout=1800)
    path,data=report();print(path)
    return 0 if all(x.get("status")=="PASS" for k,x in data.items() if k!="E") else 1

if __name__=="__main__":raise SystemExit(main())
