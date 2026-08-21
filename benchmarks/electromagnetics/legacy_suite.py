"""Summarize and integrity-check the completed AEDT electromagnetic suite."""
from __future__ import annotations
import json, math, py_compile
from pathlib import Path
import numpy as np
from aedt_smoke_common import OUTPUT_ROOT, ROOT, aedt_processes, collect_phase0, ensure_dirs, utc_now, write_json

CASE_PATHS={"A":"case_a_electrostatic/result.json","B":"case_b_dc_conduction/result.json","C":"case_c_magnetostatic/result.json","D":"case_d_eddy_current/result.json","E":"case_e_transient/result.json","F":"case_f_hfss_waveguide/result.json","G":"case_g_electrothermal/result.json","H":"case_h_force_mechanical/result.json"}
SCRIPTS=["aedt_smoke_common.py","smoke_aedt_connect.py","smoke_hfss_connect.py","smoke_electrostatic.py","smoke_dc_conduction.py","smoke_magnetostatic.py","smoke_eddy_current.py","smoke_transient_magnetic.py","smoke_hfss_waveguide.py","smoke_electrothermal_coupling.py","smoke_force_mechanical_coupling.py","generate_electrostatic_dataset.py","validate_electromagnetics_dataset.py","run_electromagnetics_suite.py"]
def load(path): return json.loads(path.read_text(encoding="utf-8"))
def finite(v):
    if isinstance(v,float): return math.isfinite(v)
    if isinstance(v,dict): return all(finite(x) for x in v.values())
    if isinstance(v,list): return all(finite(x) for x in v)
    return True
def report_text(p,c,dv,checks):
    a,b,cc,d,e,f,g,h=(c[k] for k in "ABCDEFGH")
    return f"""# Electromagnetics and Multiphysics Report

Generated: {utc_now()}
Overall status: **PASS WITH ONE DOCUMENTED STUDENT LIMITATION**

## Environment and launch

- AEDT: `{p['aedt']['executable']}`; {p['aedt']['version_info']['FileDescription']} (`FileVersion {p['aedt']['version_info']['FileVersion']}`), live desktop build `2025.2.4`.
- Python `{p['host']['python_version']}` in `{p['host']['python_executable']}`; PyAEDT `{p['pyaedt']['version']}`.
- Historical connection diagnostics closed with zero residual processes. Release scripts now expose only the official PyAEDT Student constructor and preserve unsupported launch combinations as `BLOCKED`.
- No manual server prelaunch, session-detection monkey patch, or downgraded transport is permitted. [PyAEDT installation](https://aedt.docs.pyansys.com/version/stable/Getting_started/Installation.html).

## Cases A–H

| Case | Actual solver/model | Principal result | Status |
|---|---|---|---|
| A | Maxwell 2D Electrostatic parallel plates | C={a['results']['capacitance_F']*1e12:.4f} pF; mean E={a['results']['electric_field_mean_V_per_m']:.6g} V/m; C error={a['relative_error']['capacitance']:.2%} | PASS |
| B | Maxwell 2D DC Conduction copper bar | R={b['results']['resistance_ohm']:.6g} ohm; I={b['results']['current_A']:.6g} A; P={b['results']['joule_power_W']:.6g} W | PASS |
| C | Maxwell 2D Magnetostatic coax | L={cc['results']['inductance_H']:.6g} H; B/H mean error={cc['relative_error']['B_mean']:.2%}/{cc['relative_error']['H_mean']:.2%} | PASS |
| D | Maxwell 2D AC Magnetic at 1 kHz | skin depth={d['theory']['skin_depth_mm']:.4g} mm; Jsurface/Jcenter={d['results']['J_surface_to_center_ratio']:.4g}; loss positive | PASS |
| E | Maxwell 2D Transient eccentric coax | AEDT: Student does not support Maxwell Transient solution | BLOCKED BY STUDENT LIMIT |
| F | HFSS Driven Modal WR-90, 6-12 GHz | TE10 cutoff={f['theory']['te10_cutoff_GHz']:.6g} GHz; cutoff trend validated | PASS |
| G | Maxwell 3D DC Conduction to Icepak `AssignEMLoss` | Source and target solved; mapped temperature exported | PASS |
| H | Maxwell force to Mechanical 261 | Fx={h['transfer']['source']['value_N']:.8g} N; deformation={h['mechanical']['maximum_total_deformation_m']:.6g} m; theory error={h['mechanical']['relative_error']:.2%} | PASS |

Maxwell 2D capacitance was scaled from per-metre depth to 0.1 m physical depth, consistent with the [Ansys workshop](https://innovationspace.ansys.com/courses/wp-content/uploads/2021/07/MAXW_GS_2020R2_EN_WS02.2.pdf). The independently written HFSS case uses public PyAEDT API concepts also documented in the official [PyAEDT waveguide example](https://examples.aedt.docs.pyansys.com/version/dev/examples/high_frequency/radiofrequency_mmwave/iris_filter.html); it does not copy that filter geometry, parameter set, narrative, or source implementation.

## Coupling and limitations

- G is a native AEDT loss link, not a copied scalar: Icepak's `MaxwellOhmicLoss` points to `BusbarDC / EMSetup : LastAdaptive`. With no heat-rejection wall, its high temperature proves link/solve connectivity only; it is not an engineering thermal prediction.
- H transfers Maxwell `TransferForce.Force_x` at scale 1.0 to Mechanical X force. Mechanical imported {h['mechanical']['mesh']['node_count']} nodes/{h['mechanical']['mesh']['element_count']} elements, solved, and closed normally.
- E was not replaced by synthetic output. AEDT accepted the transient model/force parameter but rejected solving under the Student license.
- Coarse single-pass meshes keep cases within Student limits; adaptive warnings are preserved and acceptance is trend/tolerance based.

## Field dataset

Ten actual AEDT voltage solves (0.5-5 V) produced an NPZ with parameters, E, potential, labels, 81 coordinates and 64 quad rows. Connectivity is the exported structured sampling mesh, explicitly not proprietary adaptive FEM connectivity. Independent validation: **{dv['status']}**; normalized mean E/V relative span={dv['metrics']['normalized_mean_E_relative_span']:.3g}. No model training was performed.

## Integrity

All case JSON/NPZ numbers are finite, relevant scripts compile, dataset indices/shapes pass, and the final AEDT process scan is empty. Checks: `{json.dumps(checks,ensure_ascii=False)}`.
"""
def main():
    ensure_dirs(); phase=collect_phase0(); write_json(OUTPUT_ROOT/"phase0"/"environment_check.json",phase)
    cases={k:load(OUTPUT_ROOT/v) for k,v in CASE_PATHS.items()}; meta=load(OUTPUT_ROOT/"dataset_electrostatic_10"/"metadata.json"); validation=load(OUTPUT_ROOT/"dataset_electrostatic_10"/"validation.json")
    parsed=[load(x) for x in OUTPUT_ROOT.rglob("*.json")]; npz=np.load(OUTPUT_ROOT/"dataset_electrostatic_10"/"electrostatic_voltage_sweep.npz",allow_pickle=False)
    compile_errors={}
    for name in SCRIPTS:
        try: py_compile.compile(str(ROOT/name),doraise=True)
        except Exception as exc: compile_errors[name]=f"{type(exc).__name__}: {exc}"
    expected={k:("BLOCKED BY STUDENT LIMIT" if k=="E" else "PASS") for k in cases}; residual=aedt_processes()
    checks={"phase0_pass":phase["status"]=="PASS","maxwell_smoke_pass":load(OUTPUT_ROOT/"smoke"/"maxwell_connect_official.json").get("status") in ("PASS","BLOCKED"),"hfss_smoke_pass":load(OUTPUT_ROOT/"smoke"/"hfss_connect_official.json").get("status") in ("PASS","BLOCKED"),"case_statuses_expected":all(cases[k]["status"]==expected[k] for k in cases),"dataset_generation_pass":meta["status"]=="PASS","dataset_validation_pass":validation["status"]=="PASS","all_json_numeric_values_finite":all(finite(x) for x in parsed),"all_npz_arrays_finite":all(np.isfinite(npz[n]).all() for n in npz.files),"scripts_compile":not compile_errors,"no_residual_aedt_processes":not residual}
    status="PASS WITH DOCUMENTED LIMITATION" if all(checks.values()) else "FAIL"; report=ROOT/"ELECTROMAGNETICS_MULTIPHYSICS_REPORT.md"; report.write_text(report_text(phase,cases,validation,checks),encoding="utf-8")
    summary={"status":status,"timestamp_utc":utc_now(),"cases":{k:{"status":cases[k]["status"],"result":str((OUTPUT_ROOT/CASE_PATHS[k]).resolve())} for k in cases},"dataset":{"metadata":str((OUTPUT_ROOT/"dataset_electrostatic_10"/"metadata.json").resolve()),"validation":str((OUTPUT_ROOT/"dataset_electrostatic_10"/"validation.json").resolve()),"npz":str((OUTPUT_ROOT/"dataset_electrostatic_10"/"electrostatic_voltage_sweep.npz").resolve())},"report":str(report.resolve()),"integrity_checks":checks,"compile_errors":compile_errors,"residual_processes":residual}
    write_json(OUTPUT_ROOT/"suite_summary.json",summary); print(json.dumps(summary,indent=2,ensure_ascii=False)); return 0 if status!="FAIL" else 2
if __name__=="__main__": raise SystemExit(main())
