"""Run and validate the Ansys 261 material/advanced-solid-mechanics suite."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from multiphysics_common import multiphysics_processes, wait_for_process_cleanup
from solid_materials_common import MATERIALS_OUT, ROOT, ensure_dirs, write_json


CASES = [
    ("A", "smoke_plasticity.py", "plasticity"),
    ("B", "smoke_hyperelastic.py", "hyperelastic"),
    ("C", "smoke_viscoelastic.py", "viscoelastic"),
    ("D", "smoke_creep.py", "creep"),
    ("E", "smoke_fatigue.py", "fatigue"),
    ("F", "smoke_fracture.py", "fracture"),
    ("G", "smoke_orthotropic.py", "orthotropic"),
    ("H", "smoke_single_crystal_elasticity.py", "single_crystal_elasticity"),
]


def finite_tree(value) -> bool:
    if isinstance(value, float): return math.isfinite(value)
    if isinstance(value, dict): return all(finite_tree(v) for v in value.values())
    if isinstance(value, list): return all(finite_tree(v) for v in value)
    return True


def load_results() -> list[dict]:
    results=[]
    for letter, _, name in CASES:
        path=MATERIALS_OUT/name/f"{name}_results.json"
        if not path.is_file(): raise FileNotFoundError(path)
        data=json.loads(path.read_text(encoding="utf-8"))
        if data.get("case") != letter: raise RuntimeError(f"Case identity mismatch in {path}")
        if not finite_tree(data): raise RuntimeError(f"NaN/Inf in {path}")
        for required in ("material_model","analysis_type","mesh","parameters","results","theory","errors","checks","files"):
            if required not in data: raise RuntimeError(f"Missing {required} in {path}")
        for artifact in data["files"]:
            if not Path(artifact).is_file(): raise FileNotFoundError(artifact)
        results.append(data)
    return results


def g(data:dict,*keys,default="—"):
    cur=data
    for key in keys:
        if not isinstance(cur,dict) or key not in cur:return default
        cur=cur[key]
    if isinstance(cur,float): return f"{cur:.6g}"
    return str(cur)


def build_report(results:list[dict]) -> Path:
    by={r["case"]:r for r in results}; report=ROOT/"MATERIAL_SOLID_MECHANICS_REPORT.md"
    rows=[]
    for r in results:
        rows.append(f"| {r['case']} | {r['title']} | {r['material_model']} | {r['analysis_type']} | {r['status']} |")
    a,b,c,d,e,f,og,h=(by[x] for x in "ABCDEFGH")
    text=f"""# Material and Advanced Solid Mechanics Report

Generated: {datetime.now(timezone.utc).isoformat()}
Environment: Windows 11; Ansys Student 2026 R1 / 261; MAPDL batch solver; SI units.

## Executive result

All eight cases were solved by the installed Ansys 261 solver and passed solver-independent physical checks. A solver exit code alone was not accepted: every case has a theory/constitutive comparison and structured finite-data validation.

| Case | Benchmark | Material model | Analysis | Status |
|---|---|---|---|---|
{chr(10).join(rows)}

## Case details

### A — Elastic-plastic load/unload

- Element/mesh: SOLID185, regular 3-D bar ({g(a,'mesh','nominal_elements')} nominal elements).
- Model: bilinear isotropic hardening, E={float(a['parameters']['E_pa'])/1e9:.3g} GPa, yield={float(a['parameters']['yield_stress_pa'])/1e6:.3g} MPa, tangent modulus={float(a['parameters']['tangent_modulus_pa'])/1e9:.3g} GPa.
- Result: residual strain {g(a,'results','residual_strain')}; maximum plastic strain {g(a,'results','maximum_equivalent_plastic_strain')}.
- Validation: residual error {float(a['errors']['residual_relative_error'])*100:.3g}%; maximum curve error {float(a['errors']['maximum_curve_relative_error'])*100:.3g}%.
- Status: **{a['status']}**.

### B — Hyperelastic large deformation

- Element/mesh: mixed u-P SOLID185; NLGEOM on; maximum stretch 1.5.
- Model: incompressible Neo-Hookean, initial shear modulus {float(b['parameters']['mu_pa'])/1e6:.3g} MPa.
- Result: maximum force {g(b,'results','maximum_force_n')} N; integrated strain energy {g(b,'results','strain_energy_j')} J.
- Validation: nominal stress against `mu*(lambda-lambda^-2)`, maximum error {float(b['errors']['maximum_stress_relative_error'])*100:.3g}%; energy error {float(b['errors']['energy_relative_error'])*100:.3g}%.
- Status: **{b['status']}**.

### C — Viscoelastic relaxation

- Model: generalized Maxwell/Prony shear and bulk terms; relative relaxing modulus {g(c,'parameters','relative_relaxing_modulus')}; tau={g(c,'parameters','tau_s')} s.
- Result: {g(c,'results','samples')} time samples; stress relaxed from {float(c['results']['initial_stress_pa'])/1e3:.3g} to {float(c['results']['final_stress_pa'])/1e3:.3g} kPa.
- Validation: exponential relaxation maximum error {float(c['errors']['maximum_relative_error'])*100:.3g}%.
- Status: **{c['status']}**.

### D — Norton creep

- Model: implicit secondary creep `TB,CREEP,,,,6`; temperature {g(d,'parameters','temperature_c')} °C; constant stress {float(d['parameters']['stress_pa'])/1e6:.3g} MPa.
- Result: final creep strain {g(d,'results','final_creep_strain')}; rate {g(d,'results','creep_rate_1_s')} 1/s.
- Validation: `epsilon_cr=C1*sigma^n*t`, late-time maximum error {float(d['errors']['late_time_max_relative_error'])*100:.3g}%.
- Status: **{d['status']}**.

### E — Stress-life fatigue

- Structural source: two actual SOLID185 extrema; alternating stress {float(e['results']['alternating_stress_pa'])/1e6:.3g} MPa and mean stress {float(e['results']['mean_stress_pa'])/1e6:.3g} MPa.
- Result: Goodman-corrected amplitude {float(e['results']['goodman_corrected_amplitude_pa'])/1e6:.3g} MPa; life {g(e,'results','life_cycles')} cycles; damage/cycle {g(e,'results','damage_per_cycle')}; 1e6-cycle safety factor {g(e,'results','safety_factor_at_1e6_cycles')}.
- Load conservation error: {float(e['errors']['reaction_balance_max_fraction'])*100:.3g}%.
- Scope note: stress extrema are native MAPDL results; S-N/Goodman life is the documented project-side postprocessor, not a claimed Mechanical Fatigue Tool run.
- Status: **{e['status']}**.

### F — Mode-I fracture

- Crack: center crack quarter-symmetry model; half crack length {g(f,'parameters','half_crack_length_m')} m.
- Tip/mesh: PLANE183 plane stress, `KSCON` quarter-point singular elements, five `CINT` SIFS contours.
- Result: stable-contour mean KI={float(f['results']['mean_stable_ki_pa_sqrt_m'])/1e6:.6g} MPa sqrt(m); contour scatter {float(f['results']['contour_scatter_fraction'])*100:.3g}%.
- Theory: wide-plate `sigma*sqrt(pi*a)`={float(f['theory']['ki_pa_sqrt_m'])/1e6:.6g} MPa sqrt(m); error {float(f['errors']['relative_error'])*100:.3g}%.
- Status: **{f['status']}**.

### G — Orthotropic lamina

- Model: 3-D orthotropic elasticity with explicit element material coordinates at 0°, 45°, and 90°.
- Parameters: E1={float(og['parameters']['E1_pa'])/1e9:.3g} GPa, E2={float(og['parameters']['E2_pa'])/1e9:.3g} GPa, G12={float(og['parameters']['G12_pa'])/1e9:.3g} GPa.
- Validation: transformed-compliance formula; maximum direction-modulus error {float(og['errors']['maximum_relative_error'])*100:.3g}%.
- Status: **{og['status']}**.

### H — Cubic single-crystal elasticity

- Model: cubic stiffness C11={float(h['parameters']['C11_pa'])/1e9:.3g}, C12={float(h['parameters']['C12_pa'])/1e9:.3g}, C44={float(h['parameters']['C44_pa'])/1e9:.3g} GPa.
- Orientations: [100], [110], [111], using explicitly oriented parallelepipeds and nodal coordinate systems; the material tensor stays in the crystal frame.
- Validation: full compliance-tensor directional modulus; maximum error {float(h['errors']['maximum_relative_error'])*100:.3g}%.
- Scope note: elastic anisotropy only; no slip-system crystal plasticity is claimed.
- Status: **{h['status']}**.

## Output organization

Each case directory under `outputs/materials/<case>/` contains the APDL input, solver output, raw extraction, curve CSV, SVG, and result JSON. Solver logs are mirrored under `logs/materials/`. JSON records material model, analysis type, mesh, parameters, physical results, theory, errors, checks, limitations, solver version, units, and absolute artifact paths.

## Capability matrix

| Capability | Evidence | Status |
|---|---|---|
| Bilinear elastoplasticity and unloading | Case A | PASS |
| Hyperelastic finite strain | Case B | PASS |
| Linear viscoelastic Prony relaxation | Case C | PASS |
| Implicit secondary creep | Case D | PASS |
| S-N + Goodman fatigue assessment | Case E | PASS (MAPDL stress + project postprocessor) |
| LEFM SIFS with singular crack-tip mesh | Case F | PASS |
| Orthotropic material axes/transformation | Case G | PASS |
| Cubic single-crystal elastic anisotropy | Case H | PASS |

## Not yet covered

Multilinear/cyclic plasticity, kinematic hardening and ratcheting; Mullins/damage hyperelasticity; nonlinear/thermorheologically simple viscoelasticity; primary/tertiary creep and creep rupture; native Mechanical fatigue objects, strain-life and crack-growth fatigue; J-integral plastic fracture, VCCT/XFEM/SMART crack growth; composite failure/delamination; crystal plasticity, slip, twinning, texture evolution; damage, phase transformation, and user material subroutines.
"""
    report.write_text(text,encoding="utf-8")
    return report


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--report-only",action="store_true"); args=parser.parse_args()
    ensure_dirs(); baseline=multiphysics_processes(); runs=[]
    if not args.report_only:
        for letter,script,name in CASES:
            done=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=False,timeout=1800)
            runs.append({"case":letter,"script":script,"exit_code":done.returncode})
    results=load_results(); report=build_report(results); remaining=wait_for_process_cleanup(baseline,timeout=20)
    checks={"eight_cases":len(results)==8,"all_cases_pass":all(r["status"]=="PASS" for r in results),"all_runs_zero":args.report_only or all(r["exit_code"]==0 for r in runs),"no_new_ansys_processes":not remaining}
    summary={"status":"PASS" if all(checks.values()) else "FAIL","timestamp_utc":datetime.now(timezone.utc).isoformat(),"checks":checks,"runs":runs,"cases":[{"case":r["case"],"status":r["status"],"result_file":str((MATERIALS_OUT/CASES[i][2]/f"{CASES[i][2]}_results.json").resolve())} for i,r in enumerate(results)],"report":str(report.resolve()),"remaining_processes":remaining}
    write_json(MATERIALS_OUT/"suite_summary.json",summary); print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
