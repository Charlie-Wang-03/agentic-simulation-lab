# MULTIPHYSICS COUPLING REPORT

All statuses below come from actual local Ansys Student 2026 R1 / 261 runs. Solver exit alone is not accepted as PASS.

## Environment

- PySystemCoupling `0.13.0`, PyMAPDL `0.74.0`, PyFluent `0.41.0`.
- System Coupling launcher: `C:\Program Files\ANSYS Inc\ANSYS Student\v261\SystemCoupling\bin\systemcoupling.bat`; server `26.1`; `ping()` `True`.
- Residual solver processes after completed tests: `[]`.

## Status

| Case | Status | Evidence / limitation |
|---|---|---|
| Phase 0 | PASS | All defined physics and data checks passed |
| A | PASS | All defined physics and data checks passed |
| B | PASS | All defined physics and data checks passed |
| C | PASS | All defined physics and data checks passed |
| D | PASS | All defined physics and data checks passed |
| E | FAIL | The actual run ends at 0.1 s. The 34-35 s periodic window, beam-tip amplitudes, frequency, and quantitative reference comparison do not exist, so benchmark PASS is not claimed. |
| F | PASS | All defined physics and data checks passed |
| G | PASS | All defined physics and data checks passed |
| H | PASS | All defined physics and data checks passed |

## Case E — Turek–Hron FSI2: FAIL

- Actual run: `dt = 0.01 s`, end time `0.09999999999999999 s`, 10 coupling steps.
- Participants/interface: Fluent `FLUENT-1` ↔ MAPDL `MAPDL-2`, `Interface-1`; Force and Incremental Displacement.
- Mapping: minimum `100.0%`.
- Persisted state: `10` System Coupling restart points and `10` Fluent case/data autosave pairs.
- Official 34–35 s reference ranges: drag `[135.71667273282532, 282.7041680786174] N/m`; lift `[-233.44481605351206, 234.1137123745819] N/m`. The 0.01 m Fluent depth is accounted for when converting N to N/m.
- Beam-tip x/y amplitudes, periodic drag/lift range, and frequency: **not available**, because 34–35 s was not reached.
- Continuation diagnosis: externally managed sessions were successfully rebound and System Coupling opened step 10 at 0.1 s, but MAPDL reported a beginning-time mismatch (`0` vs `0.1 s`). The next implementation sets MAPDL transient restart time explicitly before reconnecting; this change has not been solver-retested because the local execution request was blocked by the Codex usage limit.
- No formal benchmark comparison or PASS is claimed.

## Case G — synchronous Thermal–Fluid–Structural: PASS

- Solid participant: MAPDL transient coupled-field `SOLID226`, `KEYOPT(1)=11` (structural + thermal DOFs). Mechanical participant fallback was unnecessary.
- `FSIN_1` actual inputs: `['FORC', 'FDNS', 'TEMP', 'TBULK', 'HCOEF', 'HFLW']`.
- `FSIN_1` actual outputs: `['INCD', 'TEMP', 'TBULK', 'HCOEF', 'HFLW']`.
- Active four transfers on one interface: Fluent Force → `FORC`; Fluent Heat Flow → `HFLW`; MAPDL `INCD` → Fluent displacement; MAPDL `TEMP` → Fluent temperature.
- Mapping: minimum area `100.0%`, nodes `100.0%`, all recorded statistics `100.0%`.
- Convergence: `18` iteration records over two 0.1 s steps; maximum `10` iterations. Final transfer RMS criteria were below 0.01.
- Conservation: force relative error `0.01047412959343449` (accepted coarse-smoke tolerance 0.02); heat-flow relative error `2.968806153138808e-16`.
- Key fields at 0.2 s: fluid velocity `9.771869172332367e-06 m/s`, pressure `-0.002892628836723426 Pa`, interface temperature `300.0002242971846 K`, heat flux `-7.258353742065314 W/m²`; solid temperature `[299.9998272457019, 300.00033914747837] K`, max displacement `0.00042959636510125204 m`, max equivalent stress `1483.926467040249 Pa.
- Validation contains warnings for unused *additional* participant capabilities (FDNS/TBULK/HCOEF/TEMP input); there are no setup errors for the four active transfers.

## Case H — Case F surrogate dataset smoke: PASS

- Eight actual `Fluid → Thermal → Structural` sequences. Existing Fluent 261 CHT raw fields were reused; all eight corresponding MAPDL 261 thermal-stress analyses were actually solved.
- Parameters: inlet velocity, inlet temperature, solid conductivity, Young's modulus; wall thickness is stored with each case.
- Format: compressed NPZ per case plus `index.json` and `dataset_validation.json`.
- Per-case independent mesh/data shapes:
  - Fluid: coordinates `(671, 2)`, connectivity `(600, 4)`, velocity `(671, 3)`, pressure/temperature `(671,)`.
  - Solid: coordinates `(84, 3)`, connectivity `(20, 8)`, temperature/equivalent stress `(84,)`, displacement `(84, 3)`.
  - Interface: coordinates `(61, 2)`, temperature/heat flux/pressure `(61,)`.
- Dataset ranges: solid temperature `[300.06550094, 303.66065655999995] K`, displacement magnitude `[0.0, 9.767087123470842e-07] m`, equivalent stress `[210275.80683109327, 2411040.607895871] Pa.
- Validator result: `PASS`; case count `8`. It checks field-to-mesh shapes, connectivity bounds, units, parameter/solver metadata, NaN/Inf, physical temperature and nonzero structural response, interface fields, explicit time, and independent domain meshes.

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
