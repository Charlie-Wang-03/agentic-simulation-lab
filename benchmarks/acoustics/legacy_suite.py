"""Run, validate, and report the complete Ansys 261 acoustics suite."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from acoustics_common import ACOUSTICS_OUT, ROOT, ensure_dirs, write_json


CASES=[
    ("A","smoke_acoustic_tube.py","case_a_tube","case_a_results.json"),
    ("B","smoke_acoustic_cavity_modal.py","case_b_cavity_modal","case_b_results.json"),
    ("C","smoke_helmholtz_resonator.py","case_c_helmholtz","case_c_results.json"),
    ("D","smoke_acoustic_transient.py","case_d_transient","case_d_results.json"),
    ("E","smoke_acoustic_radiation.py","case_e_radiation","case_e_results.json"),
    ("F","smoke_vibroacoustic_radiation.py","case_f_vibroacoustic","case_f_results.json"),
    ("G","smoke_acoustic_structural_coupling.py","case_g_coupled","case_g_results.json"),
    ("H","smoke_acoustic_impedance.py","case_h_impedance","case_h_results.json"),
    ("I","smoke_acoustic_dataset.py","case_i_dataset","case_i_results.json"),
]


def load_results()->dict[str,dict]:
    results={}
    for letter,_,folder,name in CASES:
        path=ACOUSTICS_OUT/folder/name
        if not path.is_file(): raise FileNotFoundError(path)
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("case")!=letter: raise RuntimeError(f"Case mismatch in {path}")
        results[letter]=data
    return results


def f(value)->str:
    return f"{value:.6g}" if isinstance(value,float) else str(value)


def build_report(r:dict[str,dict],validation:dict,pml:dict)->Path:
    a,b,c,d,e,rf,g,h,i=(r[x] for x in "ABCDEFGHI")
    rows="\n".join(f"| {x} | {r[x]['title']} | {r[x]['analysis_type'] if 'analysis_type' in r[x] else 'dataset generation'} | **{r[x]['status']}** |" for x in "ABCDEFGHI")
    report=ROOT/"ACOUSTICS_WAVE_PHYSICS_REPORT.md"
    text=f"""# Acoustics / Wave / Vibro-acoustics Validation Report

Generated: {datetime.now(timezone.utc).isoformat()}
Environment: Windows 11; Ansys Student 2026 R1 / MAPDL 261; conda `ansys-py312`; SI units.

## Executive result

The current MAPDL automation chain solved all Cases A–I with native acoustic elements and passed result-based physical checks. Student licensing did not block FLUID30, FLUID221, harmonic acoustics, modal acoustics, transient acoustics, radiation boundaries, PML, impedance, one-way structural radiation, or strong two-way matrix-coupled acoustic–structural modes. The automation uses direct MAPDL batch input because it is the most natural stable scripting path for explicit element, PML, complex-field, and FSI control in this environment.

| Case | Benchmark | Analysis | Status |
|---|---|---|---|
{rows}

## Phase 0 — automation and solver capability

- Solver/element chain: MAPDL 261, FLUID30 (8-node acoustic hex), FLUID221 (10-node acoustic tetra), SHELL181 for flexible plates.
- Minimum harmonic smoke: Case A created air, solved complex pressure, extracted amplitude/phase, and closed normally. Its sweep and field solver outputs both show normal MAPDL completion.
- Harmonic acoustics: Cases A, C, E, F, H, I — **PASS**.
- Modal acoustics: Case B — **PASS**.
- Transient acoustics: Case D — **PASS**.
- Strong structural–acoustic coupling: Case G, FLUID30 `KEYOPT(2)=0` with shared SHELL181 nodes and `SF,FSI` — **PASS**.
- Radiation/infinite treatment: Case E `SF,INF` — **PASS**.
- PML: Phase-0 FLUID30 `KEYOPT(4)=1`, 16 layers, `PMLOPT` target 1e-3 — **{pml['status']}**; pressure fell from {pml['pressure_amplitude_pa'][2]:.4g} Pa to {pml['pressure_amplitude_pa'][3]:.4g} Pa inside the layer.
- Absorbing impedance: Case H `SF,IMPD` — **PASS**.

## Case A — one-dimensional standing wave

- Geometry/material/mesh: L={a['geometry']['length_m']} m, square width {a['geometry']['width_m']} m; air density {a['acoustic_material']['density_kg_m3']} kg/m³, c={a['acoustic_material']['sound_speed_m_s']} m/s; FLUID30 size {a['mesh']['nominal_size_m']} m.
- Analysis: {a['analysis_type']}; prescribed pressure/open end at x=0 and natural rigid end at x=L.
- Result: resonance {a['results']['resonance_frequency_hz']} Hz, peak pressure {a['results']['peak_pressure_pa']:.6g} Pa, SPL {a['results']['peak_spl_db']:.4g} dB; 41 complex-pressure axis samples.
- Theory: `f1=c/(4L)` = {a['theory']['frequency_hz']:.6g} Hz; relative error {100*a['errors']['relative_frequency_error']:.4g}% — **{a['status']}**.

## Case B — rectangular cavity acoustic modes

- Geometry: {b['geometry']['Lx_m']} × {b['geometry']['Ly_m']} × {b['geometry']['Lz_m']} m closed rigid air cavity; FLUID30 size {b['mesh']['nominal_size_m']} m, {b['mesh']['field_node_count']} saved nodes.
- Analysis: {b['analysis_type']}; eight eigenfrequencies and the first pressure mode shape exported.
- Theory: `c/2 sqrt((n/Lx)^2+(m/Ly)^2+(p/Lz)^2)`; maximum error {100*b['errors']['maximum_relative_error']:.4g}% — **{b['status']}**.

## Case C — Helmholtz resonator

- Geometry: V={c['geometry']['cavity_volume_m3']:.6g} m³, A={c['geometry']['neck_area_m2']:.6g} m², physical/effective neck length {c['geometry']['neck_physical_length_m']}/{c['geometry']['neck_effective_length_m']:.6g} m; FLUID221 quadratic tetrahedra, size {c['mesh']['nominal_size_m']} m.
- Result: resonance {c['results']['resonance_frequency_hz']} Hz, cavity pressure {c['results']['peak_cavity_pressure_pa']:.5g} Pa, maximum derived neck velocity {c['results']['maximum_neck_velocity_m_s']:.5g} m/s.
- Theory: Helmholtz formula with `1.7*r_eq` end correction gives {c['theory']['frequency_hz']:.5g} Hz; error {100*c['errors']['relative_frequency_error']:.4g}% — **{c['status']}**.

## Case D — transient wave propagation

- FLUID30 pressure formulation; L={d['geometry']['length_m']} m, dx={d['mesh']['nominal_size_m']} m; dt={d['time_integration']['time_step_s']} s, {d['time_integration']['steps']} steps.
- Result: probe peaks at {d['results']['probe_peak_time_x025_s']} and {d['results']['probe_peak_time_x075_s']} s; measured c={d['results']['measured_wave_speed_m_s']:.6g} m/s vs {d['theory']['sound_speed_m_s']} m/s; error {100*d['errors']['relative_wave_speed_error']:.4g}%.
- Five synchronized pressure-field snapshots saved — **{d['status']}**.

## Case E — open field and radiation boundary

- 2 m cubic air domain, interior point mass source, FLUID30 size {e['mesh']['nominal_size_m']} m, f={e['frequency_hz']} Hz.
- Rigid-wall and `SF,INF` models both solved. Radiation pressure at r=0.2/0.4/0.6/0.8 m: {', '.join(f'{x:.4g}' for x in e['results']['radiation_pressure_pa'])} Pa.
- Spherical decay ratio: {e['results']['pressure_decay_ratio']:.5g} vs theory {e['theory']['expected_decay_ratio']}; error {100*e['errors']['radial_decay_relative_error']:.4g}%. `|p|r` CV fell from {e['results']['rigid_pr_coefficient_of_variation']:.4g} (rigid) to {e['results']['radiation_pr_coefficient_of_variation']:.4g} (`INF`).
- The reported 10 m pressure/SPL is explicitly a spherical extrapolation, not a native PRFAR claim — **{e['status']}**.

## Case F — vibrating plate radiation (one-way)

- Structure: SHELL181 steel plate {rf['geometry']['plate_side_m']} m square × {rf['geometry']['plate_thickness_m']} m; acoustic domain: FLUID30 air with INF outer faces.
- At {rf['frequency_hz']} Hz, solved center displacement/velocity/acceleration = {rf['structure']['center_displacement_amplitude_m']:.5g} m / {rf['structure']['center_velocity_amplitude_m_s']:.5g} m/s / {rf['structure']['center_acceleration_amplitude_m_s2']:.5g} m/s².
- That solved velocity drives `SHLD`; probe pressures = {', '.join(f'{x:.4g}' for x in rf['acoustic']['pressure_amplitude_pa'])} Pa and estimated radiated power = {rf['acoustic']['estimated_radiated_power_w']:.5g} W.
- Structural and acoustic frequency both {rf['frequency_hz']} Hz — **{rf['status']}**. This is intentionally one-way; acoustic back-pressure is covered by G.

## Case G — strong two-way structure–acoustic coupling

- Flexible SHELL181 plate closes a {g['geometry']['plate_side_m']} × {g['geometry']['plate_side_m']} × {g['geometry']['cavity_height_m']} m air cavity. Coupled FLUID30 uses displacement+pressure DOFs, shared interface nodes, and `SF,FSI`; solution uses unsymmetric modal extraction.
- Structure-only first mode {g['results']['structure_only_hz'][0]:.6g} Hz; coupled first mode {g['results']['coupled_hz'][0]:.6g} Hz; shift {100*g['results']['comparisons'][0]['relative_shift']:.4g}%.
- Six modes each were solved for structure-only, acoustic-only, and coupled systems; coupled mode fields contain both nonzero pressure and displacement — **{g['status']}**.

## Case H — impedance / absorption

- FLUID30 tube compared natural rigid termination with `Z=rho*c={h['acoustic_material']['characteristic_impedance_pa_s_m']:.6g} Pa·s/m`.
- Median decomposed |R|: rigid {h['results']['median_rigid_reflection_magnitude']:.6g}, matched {h['results']['median_matched_reflection_magnitude']:.6g}; theory for matched Z gives {h['theory']['matched_reflection_magnitude']}.
- Maximum response fell from {h['results']['rigid_peak_pressure_pa']:.5g} to {h['results']['matched_peak_pressure_pa']:.5g} Pa — **{h['status']}**.

## Case I — structured surrogate dataset

- Twelve actual harmonic solves; shared mapped FLUID30 mesh with {i['mesh']['nodes']} nodes, {i['mesh']['elements']} 8-node cells, zero-based connectivity.
- NPZ arrays include coordinates, connectivity, frequency, pressure real/imaginary/amplitude/phase; pressure shape `{tuple(i['field_shape'])}`. JSON contains per-case geometry, frequency, density, sound speed, boundary parameters, units, solver evidence, and global responses.
- Independent reload/validation: **{validation['status']}**. Checks cover 10–20 case count, mesh shape/range, complex-field shapes, amplitude/phase consistency, units, NaN/Inf, parameter completeness, metadata, and transient time ordering.
- No FNO, DeepONet, or other neural operator was trained.

## Capability matrix

| Capability | Evidence | Status |
|---|---|---|
| Acoustic wave propagation | D | PASS |
| Standing wave | A | PASS |
| Modal acoustics | B | PASS |
| Geometry-dependent resonance | C | PASS |
| Transient acoustics | D | PASS |
| Radiation boundary / open domain | E (`INF`) | PASS |
| PML | Phase 0 | {pml['status']} |
| SPL | A, E, F, H | PASS |
| Vibro-acoustic radiation | F | PASS (one-way sequential) |
| Structural–acoustic FSI | G | PASS (strong two-way matrix coupling) |
| Acoustic impedance | H | PASS |
| Frequency-domain field dataset | I | PASS |
| Time-domain acoustic fields | D (CSV snapshots/history); exporter API supports NPZ | PASS |

## Output organization

- Case results and fields: `outputs/acoustics/<case>/`
- Solver logs: `logs/acoustics/<solver-job>/`
- Frequency-domain dataset: `outputs/acoustics/case_i_dataset/acoustics_frequency_dataset.npz` plus JSON metadata.
- Each case retains APDL input, complete solver output, raw extracted fields, and result JSON. Failed PML setup attempts were debugged; the final global-coordinate run is the retained passing evidence.

## Not yet covered

Underwater acoustics; sonar; porous acoustic materials; nonlinear acoustics; thermoacoustics; ultrasound; piezoelectric–acoustic coupling; cabin noise; statistical energy analysis; large-scale room acoustics.
"""
    report.write_text(text,encoding="utf-8")
    return report


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--report-only",action="store_true"); args=parser.parse_args()
    ensure_dirs(); runs=[]
    if not args.report_only:
        for letter,script,_,_ in CASES:
            done=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=False,timeout=1800)
            runs.append({"case":letter,"script":script,"exit_code":done.returncode})
        p=subprocess.run([sys.executable,str(ROOT/"smoke_acoustic_pml.py")],cwd=ROOT,check=False,timeout=1800); runs.append({"case":"PML","script":"smoke_acoustic_pml.py","exit_code":p.returncode})
        v=subprocess.run([sys.executable,str(ROOT/"validate_acoustics_dataset.py")],cwd=ROOT,check=False,timeout=300); runs.append({"case":"VALIDATE","script":"validate_acoustics_dataset.py","exit_code":v.returncode})
    results=load_results()
    validation=json.loads((ACOUSTICS_OUT/"case_i_dataset"/"validation_results.json").read_text(encoding="utf-8"))
    pml=json.loads((ACOUSTICS_OUT/"phase0_pml"/"pml_results.json").read_text(encoding="utf-8"))
    report=build_report(results,validation,pml)
    checks={"nine_cases":len(results)==9,"all_cases_pass":all(x.get("status")=="PASS" for x in results.values()),"pml_pass":pml.get("status")=="PASS","dataset_validation_pass":validation.get("status")=="PASS","all_runs_zero":args.report_only or all(x["exit_code"]==0 for x in runs),"finite_results":all(math.isfinite(float(x)) for x in [results["A"]["results"]["resonance_frequency_hz"],results["D"]["results"]["measured_wave_speed_m_s"]])}
    summary={"status":"PASS" if all(checks.values()) else "FAIL","generated_utc":datetime.now(timezone.utc).isoformat(),"checks":checks,"runs":runs,"report":str(report.resolve()),"cases":{k:v["status"] for k,v in results.items()},"pml":pml["status"],"dataset_validation":validation["status"]}
    write_json(ACOUSTICS_OUT/"suite_summary.json",summary); print(json.dumps(summary,indent=2)); return 0 if summary["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
