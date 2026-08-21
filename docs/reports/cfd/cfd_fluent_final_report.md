# Fluent CFD final smoke report — Cases M–S

Run date: 2026-08-11 to 2026-08-12. Environment: Windows 11, Ansys Fluent Student 2026 R1 / 261, PyFluent 0.41.0, Python 3.12 in `ansys-py312`. All Fluent sessions used the existing headless launcher and child-process-only `AWP_ROOT261`; no global environment variables or GUI automation were used.

## Executive result

Cases M–S all pass their stated smoke-test criteria. This round actually exercised two RANS closures, three-dimensional transient WALE LES, a two-zone nonconformal sliding mesh, air–water VOF, three-species transport, Fluent FW-H configuration plus pressure-spectrum processing, a nine-point aerodynamic parameter search, and 1/2/4-core Fluent launches. The final audit independently reloads all seven result JSON files and both time-space NPZ datasets.

These are automation and physics-sanity benchmarks, not engineering-certification studies. The limitations in the last section are part of the result, not hidden exclusions.

## Case results

| Case | Fluent model and method | Mesh / run controls | Key physical result and check | Data export | Status |
|---|---|---|---|---|---|
| M | 2-D turbulent backward-facing step, Re_h=5,000. Realizable k-ε with enhanced wall treatment versus k-ω SST; steady pressure-based solver. | 16,320 structured quads, 17,593 nodes; up to 900 requested iterations per model, with Fluent stopping on convergence. | Reattachment length 6.815h (realizable k-ε) and 7.250h (SST). Mean y+=3.493 and 3.533; maxima 5.294 and 4.525. Both models show separation, wall-shear sign change, and plausible benchmark-scale reattachment. | Velocity profiles, wall shear, y+, turbulent kinetic energy and model-specific ε/ω; CSV/NPZ/SVG and case files. | **PASS** |
| N | 3-D transient cylinder wake, Re=1,000, WALE LES; second-order transient workflow, two Fluent processes. | 24,576 extruded O-grid hexes, 28,512 nodes; span=2D; Δt=0.025D/U, 640 steps, t=16; estimated max CFL=1.25; statistics t=8–16. | Mean Cd=0.8047, Cl_rms=0.01942, dominant f=0.12346U/D and St=0.12346. Nonzero periodic lift and a resolved three-dimensional wake confirm the LES/time-series chain. This coarse LES is not a grid-converged reference solution. | 160 force samples; five snapshots at t=8,10,12,14,16. Time-space NPZ contains xyz, u/v/w, p and vorticity. | **PASS** |
| O | 2-D transient rotating flow with an actual rotating cell zone, stationary cell zone and nonconformal sliding interface. | 4,608 quads, 4,864 nodes; rotor 2,048 cells, stator 2,560; ω=20 rad/s (190.986 rpm); Δt=0.002 s, 400 steps, t=0.8 s, 157.08 steps/revolution. | Interface overlap reported as 100%. Late mean torque=-0.1681 N·m per metre; peak-to-peak torque=2.7472 N·m per metre. The nonzero periodically varying torque verifies mesh motion and interface transfer. | Torque history and four pressure/velocity snapshots at 0.5–0.8 s; CSV/SVG and case file. | **PASS** |
| P | 2-D closed-tank air–water VOF dam-break with gravity; transient pressure-based solver. | 7,500 quads, 7,701 nodes; tank 3×1 m, initial water column 0.6×0.8 m; Δt=0.005 s, 200 steps, t=1 s. | Water front advances to x=3.0 m. Volume fraction remains within [0,1]. Nodal mean α changes from 0.16047 to 0.17142, a 6.82% proxy drift below the fixed 8% smoke limit. This is a nodal sampling proxy, not an exact cell-volume mass integral. | Five snapshots; xy, u/v, p and water volume fraction in time-space NPZ; front history and SVG. | **PASS** |
| Q | 2-D laminar Species Transport mixing channel; `mixture-template` with H2O/O2/N2, convection and diffusion, no reaction. | 12,000 quads, 12,261 nodes; two half-height inlets; 1,000 maximum requested iterations, convergence observed at iteration 56. | H2O stays in [0,1]; maximum |ΣYi−1|=5.0×10⁻¹¹. Outlet H2O standard deviation falls below the unmixed 0.5 value and the mixing layer is present. | Coordinates, velocity, pressure and species mass fractions; raw/profile CSV, finite NPZ, SVG and case file. | **PASS** |
| R | Fluent native FW-H model configured on the Case H cylinder source surface with an observer at (2,0.5,0) m; Hanning-window spectrum from the converged transient pressure history. | Reuses Case H 5,632-cell transient cylinder solution; analysis window t=80–120, 161 samples. | Pressure RMS=0.1195 Pa. Dominant pressure and lift frequencies both equal 0.14907U/D; frequency difference is zero and agrees with vortex shedding. | Observer signal, FFT spectrum CSV/SVG, and a Fluent case proving FW-H source/observer configuration. | **PASS*** |
| S | S1: NACA 0012 SST AoA search maximizing Cl/Cd. S2: identical Re=100 cavity launched with 1, 2 and 4 Fluent processes. | S1: nine AoAs; five new Fluent solves plus four verified Case J results. S2: 1,600 quads; 400 maximum requested iterations, all transcripts converge at iteration 36. Timing includes launch, initialization, solve and export. | Best sampled point: AoA=5°, Cl=0.46698, Cd=0.040244, Cl/Cd=11.6036. Wall time: 21.527/22.392/23.511 s for 1/2/4 cores. Center-u relative differences: 0/3.80×10⁻⁶/1.36×10⁻⁵. Small-case launch/communication overhead dominates, so no speedup is claimed. | Complete ranking CSV and objective SVG; per-core raw fields, timing CSV and scaling SVG. | **PASS** |

\* Case R's PASS means the native FW-H source/observer setup and the CFD-pressure-to-spectrum automation chain were verified. A new FW-H propagation history was not marched and recorded; the spectrum is derived from the existing near-field Case H probe pressure. It must not be interpreted as a validated far-field SPL prediction.

## RANS and near-wall comparison

The same mesh and boundary conditions were retained in Case M, so the reattachment difference is attributable primarily to closure and near-wall behavior. SST predicts a 6.38% longer reattachment length than realizable k-ε. Both solutions export finite y+, wall shear and turbulence fields; y+ near 3.5 places this smoke mesh in the near-wall transition region and confirms field availability, but it is not a formal wall-resolution study.

## Transient statistics and time-space data

Case N records Δt, CFL estimate and an eight-convective-time statistics window. Case O covers about 2.55 rotor revolutions. Case P records five uniformly ordered snapshots through t=1 s. No separate time-step refinement campaign was performed; stability, finite fields, bounded multiphase fraction and coherent temporal signals are the acceptance evidence.

The common `fluent_field_export.py` layer now recognizes velocity_x/y/z, pressure, temperature, density, turbulent kinetic energy, ε, ω, vorticity, wall y+, species mass fraction and volume fraction when Fluent exposes them. Missing physical fields are not fabricated.

| Dataset | Coordinates | Time | Field arrays | Reload checks |
|---|---:|---:|---|---|
| `fluent_les_des_timespace_dataset.npz` | (3168,3) | (5,) | u, v, w, p, vorticity: each (5,3168) | finite, metadata valid, strictly increasing time |
| `fluent_vof_timespace_dataset.npz` | (7701,2) | (5,) | u, v, p, volume_fraction: each (5,7701) | finite, α bounded, metadata valid, strictly increasing time |

`run_fluent_final_suite.py --audit-only` performs an independent reload and shape/NaN/time/metadata audit without launching Fluent. Running it without the option reruns M through S in order and stops on the first failure.

## Optimization and parallel execution

The nine-point S1 search covers AoA=-5,-2,0,2,5,7,10,12,15 degrees. The sampled objective increases to 5° and then decreases as drag grows, yielding the reported 5° optimum. This is a discrete ranking loop, not a gradient or global optimizer.

S2 proves that PyFluent can request and run 1, 2 and 4 processes under the installed Student license. All three results agree to better than 1.4×10⁻⁵ in center velocity. Since the mesh has only 1,600 cells and the measurement includes process launch, the observed speedups of 0.961 and 0.916 for 2 and 4 cores are expected overhead-dominated results, not a scalability failure.

## CFD capability matrix after Cases A–S

| Capability | Actual coverage | State |
|---|---|---|
| Basic internal / external flow | 2-D/3-D laminar and turbulent channels, pipes, cylinders and wind tunnel | Completed |
| RANS | k-ε, realizable k-ε, k-ω SST; wall shear, y+ and turbulence fields | Completed at smoke level |
| LES / DES | 3-D transient WALE LES cylinder | **LES completed; DES/IDDES not run** |
| Unsteady flow | Vortex shedding, probes, spectra, snapshots and statistical windows | Completed |
| Aerodynamics | NACA 0012 AoA sweep, Cl/Cd/Cp and sampled optimization | Completed at benchmark level |
| Compressible flow | Ideal-gas converging–diverging nozzle and isentropic checks | Completed |
| Buoyancy flow | Boussinesq natural-convection cavity with energy equation | Completed |
| Rotating machinery | Prescribed rotating zone, torque and periodic flow | Completed at simplified 2-D level |
| Dynamic / sliding mesh | Two-zone nonconformal sliding interface | Sliding mesh completed; general deforming/overset mesh not covered |
| Multiphase / VOF | Air–water dam-break, gravity, bounded α and snapshots | Completed at smoke level |
| Species / reaction | Three-species convection–diffusion and ΣYi conservation | Species completed; finite-rate reaction/combustion not verified |
| Acoustics | Native FW-H configuration and pressure/lift spectral frequency matching | Configuration/signal chain completed; far-field prediction not validated |
| Parameter scan / optimization | 9-point aerodynamic objective ranking | Completed at discrete-search level |
| Neural-surrogate data generation | Steady parameter datasets plus LES and VOF time-space NPZ with metadata | Completed at smoke level |
| Parallel computing | 1/2/4-process control, timing and physical consistency | Completed on one workstation |

## Explicitly not covered in this round

- CHT, FSI and thermal–fluid–solid coupling are intentionally deferred to the next multiphysics category.
- Finite-rate chemistry, premixed/non-premixed combustion, radiation–combustion coupling and pollutant models were not run.
- DES/IDDES, wall-resolved LES, DNS, transition models and formal grid/time-step convergence remain open.
- Overset meshes, arbitrary deforming meshes, six-degree-of-freedom motion and production turbomachinery stage interfaces remain open.
- Eulerian multiphase, mixture models, cavitation, boiling/condensation, particle tracking and population balance remain open.
- Validated far-field SPL/directivity, porous acoustics and aeroelastic acoustics remain open.
- Adjoint/shape optimization, uncertainty quantification, distributed HPC scaling and scheduler-based production runs remain open.

## Reproducibility and outputs

- Result JSON: `outputs/fluent_rans_models.json` through the corresponding Case S JSON.
- Numerical CSV, NPZ, SVG and Fluent case/mesh files: `outputs/`.
- Successful full run logs: `logs/run_case_m.log`, `run_case_n_meshfix.log`, `run_case_o_motionfix.log`, `run_case_p_physicsfix.log`, `run_case_q_retest.log`, `run_case_r.log`, and `run_case_s.log`.
- Earlier failed debug logs are retained intentionally as an audit trail; only the final listed runs support PASS.
- Full rerun/audit entry point: `run_fluent_final_suite.py`.

Final outcome: **Case M PASS, N PASS, O PASS, P PASS, Q PASS, R PASS, S PASS.**
