# SPH / Free-Surface Verification Report

## Executive result

The executable, scriptable SPH product on this machine is **Ansys Rocky Student 26.1.0 (2026 R1)**. No standalone FreeFlow executable or application entry was found. Rocky's supported built-in PrePost scripting path created and solved native SPH projects; `ansys-rocky-core 0.4.1` exposes no SPH objects and its RPC connection resets after handshake on this installation, so PyRocky was not used to pretend that unsupported SPH automation worked.

Result: **10 PASS, 2 explicitly BLOCKED, 0 unexpected FAIL** for Cases A–L. The two blocks are non-Newtonian rheology (F) and synchronized SPH–elastic-structure coupling (I). No home-grown substitute solver and no GUI automation was used.

## Phase 0: product and API evidence

- Executables used: `Rocky.exe` / `RockySolver.exe`, version 26.1.0, build 44349.
- License evidence: real `rocky_preppost` and `rocky_solver` feature checkouts occurred during solve launches.
- Supported native formulations reported by the runtime: WCSPH, IISPH and DFSPH; Wendland/cubic/quintic kernels; explicit/implicit viscous integration; laminar/LES; Cleary/custom thermal transfer.
- Minimal smoke: 26 WCSPH water elements, gravity enabled, 0–0.02 s. Final vertical speed was approximately -0.196 m/s, consistent with `g t`; position, velocity, pressure, density, mass and element ID were extracted before a normal exit.
- Hardware from the Rocky solver log: 4 CPU processes on Intel Core Ultra 9 290HX Plus; `Use GPU: 0`. Representative internally selected time steps were 5.18e-6 s (Phase 0), 5.86e-6 s (IISPH dam break) and 2.34e-5 s (WCSPH jet). Output intervals are intentionally much larger than solver time steps.
- The normal workspace sandbox prevents Rocky from writing required license/runtime state under AppData, so suite execution requires a normal host launch. This is an execution-environment constraint, not a solver failure.

## Case results

| Case | Status | Formulation / size | Key result |
|---|---|---|---|
| A hydrostatics | PASS | IISPH, 10 mm, 73 elements | Layer-averaged pressure RMSE = 41.2% of hydrostatic head; mass drift 0; maximum density deviation 1.23e-8; mean speed 0.0355 m/s. |
| B dam break | PASS | IISPH, 10 mm, 103 elements | Front advanced from -0.090 m to +0.150 m by 0.6 s; mass drift 0; 13 raw snapshots and a `[13,31,61,4]` X-Z projection. |
| C sloshing | PASS | IISPH, 7.5 mm | First-mode theory 2.944 Hz. Surface response was 2.72 mm at 1.472 Hz and 9.58 mm near resonance; ratio 3.52. Excitation began after 0.5 s settling. |
| D free jet impact | PASS | WCSPH, 7.5 mm, up to 100 elements | Peak native particle pressure 31.6 kPa; wet-radius proxy expanded beyond the 12 mm jet; inlet momentum-flux force scale 0.0702 N. The headless wall object did not expose a native wall-force curve, so this limitation is retained explicitly. |
| E moving piston | PASS | IISPH, 10 mm, 73 elements | A 0.15 m/s piston increased horizontal kinetic energy, deformed the free surface and produced a particle-momentum reaction-force peak of about 0.195 N. |
| F non-Newtonian | BLOCKED (current product mode) | — | Rocky's callable fluid material is constant-viscosity; no power-law/Herschel–Bulkley or rheology module appeared before/after a real beta restart. Standalone FreeFlow is absent. No substitute was run. |
| G thermal SPH | PASS | IISPH, 10 mm, 73 elements | Hot water cooled from 353.150 K to 353.081 K against a 293.15 K wall. Fluid energy decreased 21.05 J; the rate inferred from native particle internal energy peaked at 42.0 W and its integral closes the global energy balance. A native wall heat-flux curve was not exposed. |
| H rigid-body entry | PASS | IISPH, 10 mm, 73 elements | Free 0.02 kg plate position/velocity/acceleration and force histories exported. Peak particle pressure 18.4 kPa; peak body `Force : Z` magnitude 0.763 N. FEM-force collection was required to expose body forces. |
| I flexible structure | BLOCKED (current API) | — | Rocky exposes System Coupling wall preprocessing and FEM-force export, but PySystemCoupling requires a host participant session while PyRocky 0.4.1 resets the real 26.1 RPC. The embedded PrePost process cannot provide that participant session. No one-way plate surrogate was substituted. |
| J resolution | PASS | IISPH, 15/10/7.5 mm | Counts 14/103/313; runtimes 20.7/20.4/22.4 s; front error to fine at 0.2 s improved from 76.9 mm (coarse) to 27.5 mm (medium); mass drift 0. Adaptive sizing is unavailable in this Rocky product mode. |
| K SPH vs VOF | PASS | IISPH vs Fluent VOF | Exactly 1:10 similar geometries. Gravity-scaled front-position RMSE = 0.215; SPH mass drift 0; Fluent volume-fraction drift 6.82%. This is macroscopic agreement, not pointwise identity. |
| L surrogate dataset | PASS | IISPH, 15 mm, 10 cases | Two initial heights × five viscosities. Every solver advanced and mass drift was 0. Raw ragged particles plus a `[time,16,31,4]` X-Z projection are retained per case. |

## Data organization and quality

The authoritative representation is a CSV ragged Lagrangian table for each case and time, containing `time_s`, stable `element_id`, XYZ position, XYZ velocity, pressure, density and mass. Temperature is included when the Rocky field exists. Dynamic counts are supported rather than forced into a false one-to-one tensor.

Each Case L run also has a compressed NPZ projection with channels `velocity_x`, `velocity_z`, `pressure`, and `occupancy`, plus coordinates, times and coverage fractions. It is explicitly derived from—not a replacement for—the raw particles.

Rocky IISPH pressure is undefined at `t=0` before the first pressure solve. Strict validation found those NaNs. The complete `t=0` snapshots were excluded from Case L rather than imputed, and the exclusion is recorded in metadata. The retained times 0.05–0.20 s pass checks for ordering, ID uniqueness, finite fields, positive mass, density within ±10% of 998.2 kg/m3, units, projection shape, coverage, occupancy bounds and NaN/Inf absence. All 10 cases pass the standalone validator.

## Capability matrix

| Capability | Result |
|---|---|
| Hydrostatics / gravity / pressure | PASS |
| Free surface and dam break | PASS |
| Sloshing resonance | PASS |
| Free jet and impact pressure | PASS |
| Moving solid boundary momentum transfer | PASS |
| Non-Newtonian SPH | BLOCKED (current product mode) |
| Thermal SPH | PASS |
| Rigid-body interaction | PASS |
| SPH–elastic-structure coupling | BLOCKED (current API) |
| Uniform resolution control | PASS |
| Adaptive sizing | Unavailable; non-required product-mode block |
| SPH–Fluent VOF comparison | PASS |
| Raw Lagrangian dataset | PASS |
| Eulerian projected dataset | PASS |

## Reproduction

Use `run_sph_free_surface_suite.py --run` from the `ansys-py312` environment for a full rerun. Use `--validate-existing` to inspect current artifacts without rerunning solvers. Rocky must be allowed to write its normal per-user license/runtime files. The unified summary is written to `outputs/sph_free_surface/suite_summary.json`; the dataset validator writes `outputs/sph_free_surface/case_l_dataset/validation_report.json`.

The focused SPH–VOF discussion is in `SPH_VOF_COMPARISON.md`.
