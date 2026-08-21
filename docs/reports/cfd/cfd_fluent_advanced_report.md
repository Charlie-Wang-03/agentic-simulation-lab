# Fluent CFD advanced smoke report — Cases G–L

Run date: 2026-08-11. Automation: `ansys-fluent-core 0.41.0`; solver: Ansys Fluent Student 2026 R1 / 261, double precision, no GUI, one solver process. The existing child-process-only `AWP_ROOT261` launcher and Fluent ASCII mesh layer were reused. All reported cases were actually run; JSON, CSV/NPZ, SVG and console logs are under `outputs/` and `logs/`.

## Results

| Case | Physics / solver | Mesh | Key result and validation | Status |
|---|---|---:|---|---|
| G | 2-D steady laminar lid-driven cavity, Re=100/1000 | 6,400 quads | Main vortex: (0.617, 0.744) and (0.520, 0.559); position errors against Ghia references 0.010L and 0.013L. Center velocities also agree at smoke-test accuracy. | PASS |
| H | 2-D transient laminar cylinder, Re=100, second-order implicit | 5,632 O-grid quads | dt=0.05D/U, 2,400 steps, statistics over tU/D=80–120. Mean Cd=1.359, Cl RMS=0.242, St=0.149. Late-window RMS ratio=1.058, confirming a periodic limit cycle. Five full-field snapshots plus 480 Cd/Cl/probe samples. | PASS |
| I | 2-D steady laminar backward-facing step, Re_h=200, expansion ratio 1.5 | 12,400 quads | Reattachment x_r/h=7.755; recirculation and wall-shear sign reversal present. Mass imbalance=0.0838%. | PASS |
| J | 2-D NACA 0012, Re_c=2e5, k-omega SST; AoA=-5,0,5,10 deg | 8,640 O-grid quads each | Cl=-0.397, 0.048, 0.467, 0.649; Cd=0.0405, 0.0214, 0.0402, 0.0866. Lift slope=4.95/rad; monotonic lift and positive drag checks pass. This is automation-grade, not wall-resolved wind-tunnel accuracy. | PASS |
| K | Case I coarse/medium/fine mesh sensitivity | 3,100 / 12,400 / 27,900 quads | x_r/h=7.693 / 7.755 / 7.762. Medium-to-fine change=0.0825%; mass imbalance decreases with refinement. | PASS |
| L | 12-case parameterized steady cavity dataset, Re=100–1200 | shared 1,600-cell / 1,681-node mesh | 12 NPZ files; every case has coordinates (1681,2), connectivity (1600,4), u/v/p (1681,). Independent full reload: consistent coordinates, valid connectivity and metadata, no NaN/Inf. | PASS |

## Numerical data and reproducibility

`fluent_field_export.py` is the common field layer. It normalizes Fluent field names, deduplicates nodal exports, stores compressed NPZ arrays and embedded JSON metadata, then immediately reloads each file. Dataset-wide validation is independent in `validate_fluent_dataset.py`. Case L metadata records units, Fluent/PyFluent versions, mesh size, parameters, solver settings and convergence state. Its index also records maximum velocity, mean kinetic energy and primary-vortex position per case.

Case H used a finite asymmetric initial y-velocity disturbance of 0.08 m/s to break exact numerical symmetry. An initial t=40 run correctly remained FAIL because shedding had not developed; t=80 still failed the stationarity check. Continuing to t=120 produced a stable limit cycle, and only t=80–120 was used for statistics. Acceptance thresholds were not relaxed.

## CFD capability coverage

| Capability group | Completed coverage |
|---|---|
| Basic CFD (prior phase) | PyFluent launcher, 2-D/3-D laminar and turbulent internal flow, cylinder external flow, numerical wind tunnel, buoyancy/energy, compressible nozzle |
| Unsteady / separation / aerodynamics | Lid-driven vortices across Re, periodic cylinder shedding and Strouhal extraction, probe histories and snapshots, backward-step separation/reattachment, NACA 0012 SST AoA sweep, Cp/Cl/Cd |
| Verification | Analytic/empirical/benchmark checks, mass conservation, periodic stationarity, mesh sensitivity, dimensionless quantities, finite-field checks |
| Dataset generation | Parameter → Fluent solve → coordinates/connectivity/u/v/p → NPZ + CSV/JSON metadata; 12 consistent cases; standalone full-reload validator |

Not yet covered: LES/DES/DNS, transition modeling, moving/deforming mesh, overset/sliding mesh, acoustics, species transport, reacting flow/combustion, radiation-coupled CFD, porous media, non-Newtonian/rheology, multiphase/cavitation, CHT, FSI, adjoint/shape optimization, UQ, HPC scaling and distributed parametric production. Those remain outside this single-phase stage.
