# Acoustics / Wave / Vibro-acoustics Validation Report

Generated: 2026-08-16T02:06:46.929094+00:00
Environment: Windows 11; Ansys Student 2026 R1 / MAPDL 261; conda `ansys-py312`; SI units.

## Executive result

The current MAPDL automation chain solved all Cases A–I with native acoustic elements and passed result-based physical checks. Student licensing did not block FLUID30, FLUID221, harmonic acoustics, modal acoustics, transient acoustics, radiation boundaries, PML, impedance, one-way structural radiation, or strong two-way matrix-coupled acoustic–structural modes. The automation uses direct MAPDL batch input because it is the most natural stable scripting path for explicit element, PML, complex-field, and FSI control in this environment.

| Case | Benchmark | Analysis | Status |
|---|---|---|---|
| A | One-dimensional standing-wave tube | full harmonic acoustic sweep | **PASS** |
| B | Three-dimensional rectangular acoustic cavity modes | modal acoustics (Block Lanczos) | **PASS** |
| C | Helmholtz resonator | full harmonic acoustic sweep | **PASS** |
| D | Transient acoustic wave propagation | full transient acoustics, pressure formulation | **PASS** |
| E | Open acoustic field with radiation boundary | full harmonic acoustics | **PASS** |
| F | Vibrating plate acoustic radiation | structural full harmonic followed by acoustic full harmonic | **PASS** |
| G | Two-way structural-acoustic coupled cavity and flexible plate | unsymmetric strong matrix-coupled modal acoustics | **PASS** |
| H | Acoustic impedance and absorbing boundary | full harmonic acoustics | **PASS** |
| I | Parametric acoustic field dataset | dataset generation | **PASS** |

## Phase 0 — automation and solver capability

- Solver/element chain: MAPDL 261, FLUID30 (8-node acoustic hex), FLUID221 (10-node acoustic tetra), SHELL181 for flexible plates.
- Minimum harmonic smoke: Case A created air, solved complex pressure, extracted amplitude/phase, and closed normally. Its sweep and field solver outputs both show normal MAPDL completion.
- Harmonic acoustics: Cases A, C, E, F, H, I — **PASS**.
- Modal acoustics: Case B — **PASS**.
- Transient acoustics: Case D — **PASS**.
- Strong structural–acoustic coupling: Case G, FLUID30 `KEYOPT(2)=0` with shared SHELL181 nodes and `SF,FSI` — **PASS**.
- Radiation/infinite treatment: Case E `SF,INF` — **PASS**.
- PML: Phase-0 FLUID30 `KEYOPT(4)=1`, 16 layers, `PMLOPT` target 1e-3 — **PASS**; pressure fell from 0.931 Pa to 0.2267 Pa inside the layer.
- Absorbing impedance: Case H `SF,IMPD` — **PASS**.

## Case A — one-dimensional standing wave

- Geometry/material/mesh: L=1.0 m, square width 0.1 m; air density 1.2041 kg/m³, c=343.24 m/s; FLUID30 size 0.025 m.
- Analysis: full harmonic acoustic sweep; prescribed pressure/open end at x=0 and natural rigid end at x=L.
- Result: resonance 86.0 Hz, peak pressure 296.169 Pa, SPL 143.4 dB; 41 complex-pressure axis samples.
- Theory: `f1=c/(4L)` = 85.81 Hz; relative error 0.2214% — **PASS**.

## Case B — rectangular cavity acoustic modes

- Geometry: 0.6 × 0.4 × 0.3 m closed rigid air cavity; FLUID30 size 0.05 m, 819 saved nodes.
- Analysis: modal acoustics (Block Lanczos); eight eigenfrequencies and the first pressure mode shape exported.
- Theory: `c/2 sqrt((n/Lx)^2+(m/Ly)^2+(p/Lz)^2)`; maximum error 1.146% — **PASS**.

## Case C — Helmholtz resonator

- Geometry: V=0.027 m³, A=0.0025 m², physical/effective neck length 0.12/0.167956 m; FLUID221 quadratic tetrahedra, size 0.025 m.
- Result: resonance 44.0 Hz, cavity pressure 52.023 Pa, maximum derived neck velocity 0.87907 m/s.
- Theory: Helmholtz formula with `1.7*r_eq` end correction gives 40.561 Hz; error 8.479% — **PASS**.

## Case D — transient wave propagation

- FLUID30 pressure formulation; L=1.0 m, dx=0.01 m; dt=2e-05 s, 150 steps.
- Result: probe peaks at 0.00102 and 0.00248 s; measured c=342.466 m/s vs 343.24 m/s; error 0.2256%.
- Five synchronized pressure-field snapshots saved — **PASS**.

## Case E — open field and radiation boundary

- 2 m cubic air domain, interior point mass source, FLUID30 size 0.1 m, f=500.0 Hz.
- Rigid-wall and `SF,INF` models both solved. Radiation pressure at r=0.2/0.4/0.6/0.8 m: 1339, 703.5, 437.3, 367.7 Pa.
- Spherical decay ratio: 0.27469 vs theory 0.25; error 9.875%. `|p|r` CV fell from 0.8725 (rigid) to 0.04478 (`INF`).
- The reported 10 m pressure/SPL is explicitly a spherical extrapolation, not a native PRFAR claim — **PASS**.

## Case F — vibrating plate radiation (one-way)

- Structure: SHELL181 steel plate 0.4 m square × 0.002 m; acoustic domain: FLUID30 air with INF outer faces.
- At 300.0 Hz, solved center displacement/velocity/acceleration = 4.5521e-07 m / 0.00085806 m/s / 1.6174 m/s².
- That solved velocity drives `SHLD`; probe pressures = 0.2354, 0.1284, 0.07418 Pa and estimated radiated power = 1.0652e-06 W.
- Structural and acoustic frequency both 300.0 Hz — **PASS**. This is intentionally one-way; acoustic back-pressure is covered by G.

## Case G — strong two-way structure–acoustic coupling

- Flexible SHELL181 plate closes a 0.4 × 0.4 × 0.3 m air cavity. Coupled FLUID30 uses displacement+pressure DOFs, shared interface nodes, and `SF,FSI`; solution uses unsymmetric modal extraction.
- Structure-only first mode 111.814 Hz; coupled first mode 113.154 Hz; shift 1.199%.
- Six modes each were solved for structure-only, acoustic-only, and coupled systems; coupled mode fields contain both nonzero pressure and displacement — **PASS**.

## Case H — impedance / absorption

- FLUID30 tube compared natural rigid termination with `Z=rho*c=413.295 Pa·s/m`.
- Median decomposed |R|: rigid 1, matched 0.00113796; theory for matched Z gives 0.0.
- Maximum response fell from 149.24 to 1.0009 Pa — **PASS**.

## Case I — structured surrogate dataset

- Twelve actual harmonic solves; shared mapped FLUID30 mesh with 84 nodes, 20 8-node cells, zero-based connectivity.
- NPZ arrays include coordinates, connectivity, frequency, pressure real/imaginary/amplitude/phase; pressure shape `(12, 84)`. JSON contains per-case geometry, frequency, density, sound speed, boundary parameters, units, solver evidence, and global responses.
- Independent reload/validation: **PASS**. Checks cover 10–20 case count, mesh shape/range, complex-field shapes, amplitude/phase consistency, units, NaN/Inf, parameter completeness, metadata, and transient time ordering.
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
| PML | Phase 0 | PASS |
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
