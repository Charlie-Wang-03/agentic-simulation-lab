# Rocky DEM / CFD–DEM validation report

Run date: 2026-08-16
Environment: Windows 11, Ansys Student 2026 R1 / 261, `ansys-py312`, SI units

## Outcome

The suite result is **PARTIAL**: Cases A–I and K physically pass; Case J is **BLOCKED** by the current API before solver launch. The independent unified validation reports 10 PASS results, one explicit block, no unexpected failures, and a passing 10-case dataset reload.

No home-grown particle integrator or synthetic CFD feedback was used. All DEM results were produced by RockySolver. Case I uses Fluent's installed official Rocky Export UDF and Rocky's `SetupOneWayFluent` F2R importer. Case J calls `SetupTwoWayFluent`; it is not replaced by an equivalent body force.

## Environment and automation chain

| Item | Verified value |
|---|---|
| Rocky executable | `C:\Program Files\ANSYS Inc\ANSYS Student\v261\rocky\bin\Rocky.exe` |
| Rocky solver | `RockySolver.exe`, version 2026.0109 / release 26.1.0, CUDA runtime 12.8 |
| Launcher | `Rocky.exe --headless --redirect-error ... --script ...` through `rocky_smoke_common.py` |
| PyRocky | `ansys-rocky-core 0.4.1` in `ansys-py312` |
| Student license | Rocky PrePost feature checked out successfully; Student limit is 32,000 DEM particles and four CPU cores |
| PyRocky RPC | **BLOCKED** (current API): the 2026 R1 server accepts the handshake and then resets the remote connection on a repeated `GetVersion`/`CreateProject` call (WinError 10054) |
| Built-in PrePost API | PASS: project/study creation, setup, solve, results, save, close and process cleanup all exercised headlessly |
| Fluent one-way plugin | PASS: 3-D Fluent solution exported to `.f2r`, mesh and data files; imported by Rocky |
| Fluent two-way plugin | **BLOCKED** (current API): installed Rocky UDF build 10261 versus Fluent build 10262 |

The common launcher records stdout, stderr, Rocky error output, return code, timeout state and elapsed time under `logs/rocky_dem/`. A timed-out 100 μm one-way tracer experiment was terminated by exact PID; the final practical non-contact tracer case uses 200 μm diameter and 1 kPa stiffness without changing drag/mass physics.

## Particle and contact models

- Shapes: Rocky-native spheres for A–F, H–K; native `sphero_cylinder` versus sphere for G.
- Material parameters are set in each case. Normal contact uses Rocky 261's native project-default normal law; restitution, static friction and dynamic friction are explicitly assigned to the material interaction. No external contact implementation is substituted.
- Rolling resistance is Rocky native `type_1` where bulk behavior is required (D–F), with the coefficient stored in each result.
- Geometry uses imported triangulated walls for collision, floor, hopper, gate and drum. Motion frames provide the timed gate translation and drum rotation.
- Solver integration timestep remains Rocky's automatically selected DEM timestep. The table below reports the explicit result-output interval, which is the sampling timestep used by every validation.

## Case results

| Case | Geometry / count | Duration; output interval | Physical check and result | Status |
|---|---|---|---|---|
| A | Free 10 mm sphere; 1 | 0.08 s; 0.01 s | Max position error `1.343e-6 m`; max velocity error `8.45e-14 m/s` against free fall | PASS |
| B | 10 mm sphere and rigid STL floor; 1 | 0.06 s; 0.0005 s | Target `e=0.7`, measured `0.699773`; contact 0.004 s; max force 1.17568 N; max overlap 1.18744 mm | PASS |
| C | Sphere on equivalent incline; 1 per run | 0.30 s; 0.005 s | `mu_s=0.5`, critical angle 26.565°. 20° holds; 35° acceleration 2.41346 versus 2.41243 m/s² | PASS |
| D | Horizontal floor and falling inlet; 69 per run | 2.0 s; 0.05 s | `mu=0.2`: 0° spread; `mu=0.6`: 20.678° pile; both settled, correct friction trend | PASS |
| E | 3-D square hopper, 24 mm outlet, sliding gate; peak 44 | 2.2 s; 0.05 s | Gate opens at 0.8 s; 0.0117621 kg discharged; mean positive flow 0.0588106 kg/s; conservation error `6.54e-16` | PASS |
| F | Closed horizontal hexagonal drum; 26, two feeds | 3.0 s; 0.10 s | Native 30 RPM motion frame; particle-plane speed rises 0.0591→0.2763 m/s; mixing index max 0.98565 | PASS |
| G | Sphere and aspect-ratio-2 sphero-cylinder; 1 each | 0.20 s; 0.005 s | Full orientation exported; final angular speeds 85.0105 versus 0.449797 rad/s; non-spherical orientation angle 2.09003 rad | PASS |
| H | 10 mm hot sphere and 300 K wall; 1 | 1.0 s; 0.05 s | Thermal model enabled; 500→481.837 K, zero monotonic violations; particle energy change -12.6804 J | PASS |
| I | 11,520-cell Fluent pipe and 200 μm tracer; 1 | 0.40 s; 0.02 s | Official F2R, Schiller–Naumann drag; velocity rises monotonically to 0.10965 m/s; 23.6% from centerline Stokes-limit estimate | PASS |
| J | Prepared 11,520-cell unsteady Fluent base | Fluent `dt=0.01 s` | Official setup fails before launch: missing `mesh_info.json`, Rocky UDF build 10261 versus Fluent build 10262; no fabricated fluidization fields | BLOCKED (current API) |
| K | 10 free-fall parameter cases; 1 dynamic particle per case | 0.05 s; 0.01 s | Diameters 8–12 mm × densities 1500/2500 kg/m³; 10/10 reload and analytical checks pass | PASS |

### Case E discharge detail

The hopper reaches 44 particles / 0.0132701 kg before the gate moves. Five particles / 0.00150796 kg remain at the last occupied sample. Discharged mass derived from inventory agrees with particle-ID count loss to machine precision. Positive discharge spans multiple output intervals rather than one deletion impulse; its coefficient of variation is 0.478 for this intentionally small, discrete inventory.

### Case F mixing definition

Species provenance is the Rocky `Particle Inlet` categorical field; `Particle Type` correctly labels both as spheres and is therefore not used as a species proxy. The reported index is `1 - instantaneous species-centroid separation / pre-rotation separation`, clipped to `[0,1]`. It changes over the active rotation window and reaches 0.98565 while the motion frame measurably drives particle speed.

### Case I official one-way coupling

Fluent reloads the validated 3-D pipe, switches it to laminar 0.1 m/s bulk flow, converges in 31 iterations, and writes a CAS/DAT pair. The installed Ansys Rocky exporter then writes `fluent_to_rocky.f2r` plus its mesh and flow-data files. Rocky reports coupling mode `fluent_one_way_steady_state` and integrates the tracer with the imported field. For the on-axis particle the theoretical local reference is the laminar circular-pipe centerline velocity, `2 U_bulk = 0.2 m/s`; the simple Stokes relaxation time is 0.31047 s. Schiller–Naumann and entrance/developing-flow effects explain the expected departure from the strict constant-field Stokes limit.

### Case J blocker

The first real call correctly rejected a steady Fluent base with `Base Setup must be Unsteady!`. Fluent was then changed to transient mode with `dt=0.01 s`, saved, and revalidated. The final `study.GetCFDCoupling().SetupTwoWayFluent(...)` call fails with:

```text
No mesh_info.json file was found.
Current Fluent build id 10262 may not be compatible with
Rocky-Fluent compiled UDFs with build id 10261.
```

Consequently packed/low-flow and near-fluidization conditions, momentum exchange, void fraction, pressure drop and bed-height sanity checks are **not run**. This is not classified as a Student particle-count limit because both products license successfully; it is a packaged Rocky–Fluent integration/build mismatch.

## Dataset organization and validation

`rocky_field_export.py` keeps the two representations separate:

- Lagrangian particles: ragged CSV rows keyed by time and particle ID, with position, translational/angular velocity, orientation, size, mass, inlet/type provenance and temperature when available.
- Eulerian CFD: Fluent mesh/field bundle retained in its native F2R files, plus separate metadata; it is not projected onto the particle table.

Case K contains 10 real Rocky cases and 50 occupied particle-time rows. `validate_rocky_dataset.py` checks case count, monotonically ordered time, IDs, finite position/velocity values, positive size/mass, units/metadata and explicitly permits changing particle counts. Standard particle outputs do not expose force components for these pre-impact cases, so no synthetic force column is inserted. Contact data is not applicable before impact.

## Capability matrix

| Capability | Evidence | Status |
|---|---|---|
| Particle dynamics / gravity | A and K analytical free fall | PASS |
| Contact / restitution | B force, overlap, duration and rebound | PASS |
| Static/dynamic friction | C critical-angle split and acceleration | PASS |
| Rolling / rotation | D–G native rolling and angular states | PASS |
| Bulk granular flow | D, E, F many-particle runs | PASS |
| Angle of repose | D friction trend | PASS |
| Hopper flow | E inventory, discharge and conservation | PASS |
| Moving walls | E timed translation; F rotation frame | PASS |
| Particle mixing | F two-feed metric and trajectories | PASS |
| Non-spherical particles | G native sphero-cylinder orientation | PASS |
| Particle thermal physics | H prescribed-temperature contact cooling | PASS |
| Fluent → Rocky one-way | I official Fluent F2R export/import | PASS |
| Fluent ↔ Rocky two-way | J official API call reaches build/metadata failure | BLOCKED (current API) |
| Eulerian–Lagrangian datasets | I metadata plus K ragged tables | PASS |
| PyRocky remote RPC | Handshake succeeds, subsequent RPC reset | BLOCKED (current API) |
| Rocky built-in headless automation | A–K project/solve/postprocessing path | PASS |

## Reproduction

Validate current artifacts:

```powershell
python run_rocky_dem_suite.py --validate-existing
```

Rerun all solver cases and CFD prerequisites:

```powershell
python run_rocky_dem_suite.py --run
```

Primary evidence is under `outputs/rocky_dem/`; process and API probes are under `logs/rocky_dem/`. The unified result is `outputs/rocky_dem/suite_summary.json`.

## Later directions (not implemented here)

Cohesive powders, adhesion, breakage/fragmentation, wear/erosion, conveyors and screw feeders, industrial mixers, dense fluidized beds, heat-transfer or reactive/combusting CFD–DEM, SPH, CFD–DEM–thermal, and DEM–structure coupling.

## Official references

- [Rocky 2026 R1 simulation and CFD-coupling parameters](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/dem_ug/set-simulation-parameters.html)
- [Rocky 2026 R1 fluidized-bed two-way tutorial](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/dem_tut/dem_tut_14.html?template=rocky)
- [Rocky 2026 R1 package and Student capability limits](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/dem_ug/package-and-version-capabilities.html)
