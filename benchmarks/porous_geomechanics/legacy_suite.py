"""Run Cases A-J, validate artifacts, and build the porous/geomechanics report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from porous_geomechanics_common import POROUS_OUT, ROOT, ensure_dirs, write_json

CASES=[
    ("A","smoke_darcy_flow.py","darcy_flow"),
    ("B","smoke_forchheimer_flow.py","forchheimer_flow"),
    ("C","smoke_anisotropic_porous.py","anisotropic_porous"),
    ("D","smoke_porous_heat_transfer.py","porous_heat_transfer"),
    ("E","smoke_porous_species.py","porous_species"),
    ("F","smoke_terzaghi_consolidation.py","terzaghi_consolidation"),
    ("G","smoke_geostatic_consolidation.py","geostatic_consolidation"),
    ("H","smoke_geomechanics_material.py","geomechanics_material"),
    ("I","smoke_thermo_poroelastic.py","thermo_poroelastic"),
    ("J","smoke_porous_dataset.py","porous_dataset"),
]

def load(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

def effective_results(preflight:dict)->list[dict]:
    blocked=preflight.get("status")=="BLOCKED BY CURRENT LICENSE CONTEXT";out=[]
    for letter,script,name in CASES:
        path=POROUS_OUT/name/f"{name}_results.json";data=load(path)
        if blocked and data.get("status")!="PASS":
            data={"case":letter,"title":data.get("title",name.replace("_"," ").title()),"status":"BLOCKED BY CURRENT LICENSE CONTEXT","error":preflight.get("fluent",{}).get("error","Ansys license preflight failed"),"result_file":str(path.resolve()),"preserved_case_result":data or None}
        elif not data:
            data={"case":letter,"title":name,"status":"NOT RUN","result_file":str(path.resolve())}
        else:
            data["result_file"]=str(path.resolve())
        out.append(data)
    return out

def val(data,*keys,default="—"):
    cur=data
    for key in keys:
        if not isinstance(cur,dict) or key not in cur:return default
        cur=cur[key]
    if isinstance(cur,float):return f"{cur:.6g}"
    return str(cur)

def build_report(preflight:dict,results:list[dict])->Path:
    by={str(r.get("case")):r for r in results};rows="\n".join(f"| {r.get('case')} | {r.get('title')} | {r.get('status')} |" for r in results)
    def cap(case):
        s=by.get(case,{}).get("status","NOT RUN")
        return "PASS" if s=="PASS" else s
    caps=[
        ("Darcy flow","A"),("Forchheimer flow","B"),("isotropic porous media","A"),("anisotropic porous media","C"),("porous heat transfer","D"),("porous species transport","E"),("pore-pressure diffusion","F"),("poroelasticity","F"),("consolidation","F"),("geostatic initialization","G"),("nonlinear soil / rock mechanics","H"),("thermo-poroelasticity","I"),("poromechanics transient dataset","J")]
    caprows="\n".join(f"| {name} | Case {case} | {cap(case)} |" for name,case in caps)
    a,b,c,d,e,f,g,h,i,j=(by[x] for x in "ABCDEFGHIJ")
    report=ROOT/"POROUS_MEDIA_GEOMECHANICS_REPORT.md"
    text=f"""# Porous Media and Geomechanics Report

Generated: {datetime.now(timezone.utc).isoformat()}
Environment: Windows 11; Ansys Student 2026 R1 / 261; PyFluent 0.41.0; PyMAPDL installed; SI units.

## Executive result

The suite contains native Fluent implementations for porous flow/heat/species (A-E), native MAPDL CPT212 implementations for consolidation/geostatic/thermo-poroelasticity (F, G, I), a native MAPDL Mohr-Coulomb plane-strain model (H), and a ten-case CPT212 dataset generator (J). Acceptance is based on analytical laws, conservation, field evolution, or yield criteria—not solver return codes alone.

Current solver preflight: **{preflight.get('status','NOT RUN')}**. {preflight.get('fluent',{}).get('error','')}

| Case | Benchmark | Status |
|---|---|---|
{rows}

## Phase 0 — actual capability check

- Fluent 261 generated settings expose porous activation, porosity, Cartesian viscous/inertial resistance vectors, equilibrium/non-equilibrium thermal controls, and anisotropic species diffusion controls.
- MAPDL 261 documents CPT212/213/215/216/217 with pore-pressure DOFs; CPT212 adds TEMP when KEYOPT(11)=1 and PRES when KEYOPT(12)=1.
- `ANTYPE,SOIL` is the native soil-analysis path. The official VM264 Terzaghi verification also intentionally uses `ANTYPE,STATIC` with physical `TIME`; Case F follows that verified formulation, while Cases G/I exercise `ANTYPE,SOIL`.
- Static settings availability is not reported as a solved PASS. The raw preflight evidence is `{POROUS_OUT/'phase0_capabilities'/'phase0_capabilities_results.json'}`.

Official references used to pin the APDL formulation: [CPT212 element](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_elem/Hlp_E_CPT212.html), [structural-pore-fluid-diffusion-thermal analysis](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_cou/Hlp_G_COU_porefluiddiffstruct.html), [VM264 input listing](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_vm/Hlp_V_VM264TXT.html), and [porous-media material data](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/ans_mat/elemdatatblpor.html).

## Case summaries and physical acceptance

### A — Darcy one-dimensional seepage

- Solver/model: Fluent, constant-density laminar flow, native porous cell zone; K=1e-8 m2, porosity 0.35, mu=1e-3 Pa s.
- Mesh: structured 80 x 8 quadrilaterals. Theory: `dp/L=mu U/K`.
- Pressure-gradient error: {val(a,'errors','pressure_gradient_relative')}; inferred-permeability error: {val(a,'errors','permeability_relative')}.
- Status: **{a['status']}**.

### B — Darcy-Forchheimer sweep

- Seven velocities span Darcy-dominated to inertial-loss regimes. Native resistance inputs are D=1e8 1/m2 and C2=2000 1/m.
- Fit: `dp/L=a U+b U2`; a={val(b,'results','fit_a_pa_s_m2')}, b={val(b,'results','fit_b_pa_s2_m3')}, R2={val(b,'results','r_squared')}.
- Artifact: `pressure_drop_vs_velocity.csv` and SVG in the Case B output directory.
- Status: **{b['status']}**.

### C — anisotropic permeability

- Native Cartesian resistance stores Kx=1e-8 m2 and Ky=2.5e-9 m2. Isotropic and anisotropic x-flow solves identify Kx; Ky is round-tripped from the native solver zone.
- The equal-x/y-gradient tensor prediction changes the flow angle from {val(c,'results','isotropic_angle_deg')} to {val(c,'results','anisotropic_angle_deg')} degrees.
- Limitation is explicit: until a solved diagonal-gradient field exists, this is a tensor-setting/identification PASS only if every recorded Case C check passes; it is never presented as a solved diagonal field.
- Status: **{c['status']}**.

### D — porous heat transfer

- Fluent local thermal-equilibrium porous channel with wall heat flux, water-like fluid properties, pressure/velocity/temperature export.
- Energy check compares wall input with `mdot cp (Tout-Tin)`; imbalance={val(d,'errors','energy_imbalance_relative')}.
- Status: **{d['status']}**.

### E — porous species transport

- Fluent transient Species Transport step tracer; output includes outlet concentration history and breakthrough curve.
- Checks enforce bounded mass fractions, sum(Yi) near one, downstream propagation, monotonic breakthrough, and t50 against the porous pore-volume residence time `phi L/U` for Fluent's superficial velocity.
- t50={val(e,'results','breakthrough_time_50pct_s')} s; pore-volume estimate={val(e,'results','expected_pore_volume_residence_time_s')} s.
- Status: **{e['status']}**.

### F — Terzaghi consolidation (core benchmark)

- MAPDL CPT212, true displacement + pore-pressure diffusion DOFs, single drainage, plane strain, top load. K is hydraulic conductivity in m/s, matching MAPDL `TB,PM,,,,PERM` units.
- Mesh/time: {val(f,'mesh','elements')} CPT212 elements; {val(f,'time','substeps')} substeps to {val(f,'time','final_s')} s.
- Multiple Tv values compare pore-pressure profiles, average degree of consolidation, and settlement against the Terzaghi Fourier series.
- Maximum profile error={val(f,'errors','maximum_profile_l2_relative')}; maximum degree error={val(f,'errors','maximum_degree_absolute')}.
- Status: **{f['status']}**.

### G — geostatic initialization plus consolidation

- MAPDL `ANTYPE,SOIL`, CPT212, solid/fluid specific weights, initial hydrostatic pore pressure, gravity/self-weight stage, then added surface load.
- Checks cover hydrostatic pressure, stress growth with depth, bulk-weight stress scale, generated/dissipating excess pressure, and developing settlement.
- Initial/final excess pressure={val(g,'results','initial_excess_pressure_pa')} / {val(g,'results','final_excess_pressure_pa')} Pa.
- Limitation: the prescribed hydrostatic field is released after initialization; without a sustained pore-fluid gravity term, the consolidation stage drains toward the zero-pressure datum.
- Status: **{g['status']}**.

### H — nonlinear geomechanics

- MAPDL PLANE182 plane strain with native Mohr-Coulomb `TB,MC`, cohesion 20 kPa, friction 30 degrees, dilation 5 degrees, and 50 kPa lateral confinement.
- Axial stress-strain, volumetric strain and equivalent plastic strain are compared with the Mohr-Coulomb compression meridian. The comparison uses an explicit 18% engineering tolerance because plane-strain confinement adds out-of-plane stress.
- Yield error={val(h,'errors','yield_relative')}.
- Status: **{h['status']}**.

### I — thermo-poroelasticity

- CPT212 KEYOPT(11)=1 and KEYOPT(12)=1, `ANTYPE,SOIL`, thermal conductivity/capacity, solid/fluid expansion, drained heated column.
- Acceptance requires simultaneously nontrivial finite temperature, pore pressure, and displacement fields; not merely three declared DOFs.
- Temperature range={val(i,'results','temperature_range_K')} K; max pore pressure={val(i,'results','maximum_pore_pressure_pa')} Pa; max displacement={val(i,'results','maximum_displacement_m')} m.
- Status: **{i['status']}**.

### J — Neural Operator / ROM dataset

- Ten native CPT212 parameter cases vary permeability, porosity, modulus and load. Each NPZ stores coordinates, connectivity, common time samples, pore pressure `[time,node]`, displacement `[time,node,component]`, stress and effective stress plus JSON metadata/global responses.
- Completed cases={val(j,'completed_cases')} / {val(j,'requested_cases')}.
- `validate_porous_dataset.py` checks case count, shapes, time order, finiteness, units, parameter metadata and pressure-dissipation direction.
- Status: **{j['status']}**.

## Output organization

- Results: `outputs/porous_geomechanics/<case>/`
- Logs: `logs/porous_geomechanics/`
- Fluent fields: coordinates, pressure, velocity, temperature/species where applicable, with porous parameters in metadata.
- MAPDL fields: coordinates, connectivity, pore pressure, displacement, stress, effective stress, and temperature where applicable.
- Transient convention: scalar `field[time,node]`; vectors/tensors append a component axis.

## Capability matrix

| Capability | Evidence | Status |
|---|---|---|
{caprows}

## Current blocking evidence

If the preflight is license-blocked, Fluent's transcript contains `Cannot initialize ANSYS Licensing context` and MAPDL's solver output contains `ANSYS LICENSE MANAGER ERROR`. This is recorded as **BLOCKED BY CURRENT LICENSE CONTEXT**, not mislabelled as a Student feature limit or API absence. Re-running the unified suite after licensing recovers will execute all cases and replace the effective statuses with physical PASS/FAIL results.

## Deferred directions

Unsaturated/Richards flow; multiphase porous flow; groundwater free surface; fractured media and hydraulic fracturing; reservoir simulation; soil-structure interaction; liquefaction; seepage failure; slopes/tunnels; granular DEM and CFD-DEM; reactive porous transport.
"""
    report.write_text(text,encoding="utf-8");return report

def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--report-only",action="store_true");args=parser.parse_args();ensure_dirs();runs=[]
    phase_path=POROUS_OUT/"phase0_capabilities"/"phase0_capabilities_results.json"
    if not args.report_only:
        done=subprocess.run([sys.executable,str(ROOT/"probe_porous_geomechanics_capabilities.py")],cwd=ROOT,check=False,timeout=1800);runs.append({"case":"Phase 0","exit_code":done.returncode})
    preflight=load(phase_path)
    if not args.report_only and preflight.get("status")!="BLOCKED BY CURRENT LICENSE CONTEXT":
        for letter,script,name in CASES:
            done=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=False,timeout=1800);runs.append({"case":letter,"script":script,"exit_code":done.returncode})
        j=load(POROUS_OUT/"porous_dataset"/"porous_dataset_results.json")
        if j.get("status")=="PASS":
            done=subprocess.run([sys.executable,str(ROOT/"validate_porous_dataset.py")],cwd=ROOT,check=False,timeout=300);runs.append({"case":"dataset validation","exit_code":done.returncode})
    results=effective_results(preflight);report=build_report(preflight,results);statuses=[r["status"] for r in results];suite_status="PASS" if statuses and all(s=="PASS" for s in statuses) else ("BLOCKED BY CURRENT LICENSE CONTEXT" if preflight.get("status")=="BLOCKED BY CURRENT LICENSE CONTEXT" else "FAIL")
    summary={"status":suite_status,"timestamp_utc":datetime.now(timezone.utc).isoformat(),"preflight":preflight,"runs":runs,"cases":[{"case":r.get("case"),"status":r.get("status"),"result_file":r.get("result_file")} for r in results],"report":str(report.resolve())};write_json(POROUS_OUT/"suite_summary.json",summary);print(json.dumps(summary,indent=2));return 0 if suite_status in ("PASS","BLOCKED BY CURRENT LICENSE CONTEXT") else 1

if __name__=="__main__":raise SystemExit(main())
