# Ansys Fluent CFD Smoke Test Report

> Advanced single-phase coverage (Cases G–L: unsteady shedding, separation,
> airfoil sweep, mesh sensitivity and surrogate-ready field datasets) is
> documented in `CFD_FLUENT_ADVANCED_REPORT.md`.

Run date: 2026-08-11 (Asia/Shanghai)
Overall result: **PASS — Phase 0 and Case A–F all passed**

## 1. Automation chain

- Python environment: `ansys-py312`, Python 3.12.13.
- PyFluent: `ansys-fluent-core 0.41.0`.
- Fluent executable: `C:\Program Files\ANSYS Inc\ANSYS Student\v261\fluent\ntbin\win64\fluent.exe`.
- Fluent-reported product version: `Ansys Fluent 2026 R1`.
- Launcher: `pyfluent.launch_fluent(product_version="261", mode="solver", ui_mode="no_gui", precision="double", fluent_path=...)`.
- `AWP_ROOT261=C:\Program Files\ANSYS Inc\ANSYS Student\v261` is injected only into Python/Fluent child-process environments. No global Windows environment was changed.
- Phase 0 executed `/report/system/proc-stats` through the PyFluent Scheme/TUI bridge; the API returned `#t` and health was `Status.SERVING`.
- The final process snapshot contained no new `fluent.exe`, `cortex.exe`, or `cx.exe` process after normal `session.exit()`.

## 2. Cases, meshes, solvers, and results

| Case | Model / solver | Mesh | Key Fluent result | Validation | Convergence | Status |
|---|---|---:|---|---|---|---|
| A — parallel plates | 2-D, steady pressure-based, constant-density air, laminar | 6,400 quads (160×40) | Δp(0.25→0.45 m)=0.042881 Pa; Umax=0.149686 m/s; ṁ/depth=0.00122117 kg/(m·s) | Poiseuille Δp error 0.150%; Umax error 0.209%; profile L2 error 0.210%; mass-flow error 0.312% | Fluent auto-converged at iteration 34 | PASS |
| B — turbulent pipe | 3-D, steady pressure-based SIMPLE, air, k–ω SST; first-order startup and velocity ramp 1→5→15 m/s | 11,520 hexes (12×12×80), D=0.02 m, L=1 m | Re=20,537.6; dp/dx=180.479 Pa/m; Darcy f=0.026192; τw=0.911844 Pa; Ubulk,out=14.99699 m/s | Blasius f=0.026430 (0.901% error); τw balance error 1.047%; native Fluent inlet/outlet mass mismatch 5.14×10⁻⁸ | Staged solution; final Fluent auto-stop at global iteration 231 | PASS |
| C — cylinder | 2-D, steady laminar, Re=40 | 10,240 O-grid quads; domain ±15D × ±10D | Cd=1.5410; Cl=−9.9×10⁻⁷; minimum wake speed=0.00848 m/s | Classic Re=40 Cd range about 1.4–1.7; symmetric lift≈0 and strong steady wake recovered | Fluent auto-converged at iteration 32 | PASS |
| D — wind tunnel | 3-D, steady air, k–ω SST, floor-mounted 1.5×1×1 m block | 18,720 body-fitted Cartesian hexes | Drag=42.1715 N; Cd=0.6885; front/rear mean p=27.60/−14.33 Pa; wake minimum=0.3299 m/s | Positive bluff-body drag, Cd in benchmark-scale range, large resolved wake deficit | Fluent auto-converged at iteration 109 | PASS |
| E — natural convection | 2-D, steady laminar Boussinesq air, energy, gravity | 2,500 quads (50×50), 0.1 m square | Ra=1.8792×10⁶; Pr=0.7068; Umax=0.06220 m/s; Nu_hot=10.9087 | Temperature remained bounded by wall temperatures; Nu within the classic Ra~10⁶ cavity range | Fluent auto-converged at iteration 332 | PASS |
| F — C-D nozzle | 2-D, steady pressure-based coupled, ideal-gas air, energy, laminar | 5,400 body-fitted quads (180×30), Ae/A*=2 | M*=0.98358; Mexit=2.19928; p*=107.736 kPa; ṁ/depth=18.0368 kg/(m·s) | Isentropic: Mexit=2.19720 (0.095% error), p*=105.656 kPa (1.97%), choked ṁ=18.6685 (3.38%) | Fluent auto-converged at iteration 113 | PASS |

Notes:

- Case C deliberately uses Re=40, where a steady symmetric wake is appropriate. Periodic vortex shedding, lift history, frequency, and Strouhal number are therefore not claimed.
- Case D is a floor-mounted block, so an aerodynamic lift result is not meaningful for this smoke benchmark; drag, pressure coefficient, surface pressure, center-plane velocity, and wake are retained.
- The final benchmark cases use one Fluent compute process for deterministic post-processing. Phase 0 also verified a two-process launch. During development, PyFluent 0.41/Fluent 261 parallel live-field extraction on custom line surfaces caused a reproducible post-processing crash; final scripts use stable Settings API ASCII export and native surface-integral queries instead.

## 3. Conservation and dimensionless checks

- Case A: extracted profile flux differs from the imposed analytical mass flow by 0.312%.
- Case B: Fluent-native inlet and outlet mass flows are 0.00575620508 and 0.00575620478 kg/s; relative imbalance is 5.14×10⁻⁸. Darcy pressure-gradient and wall-shear balance agree within 1.05%.
- Case C: Re is exactly 40 by prescribed properties; Cl is numerically zero to about 10⁻⁶.
- Case D: Reynolds number based on block height is approximately 6.85×10⁵, with a resolved separated low-speed wake.
- Case E: Ra=1.879×10⁶ and Pr=0.7068; temperature is bounded and the energy solution gives Nu=10.909.
- Case F: the throat is choked, the exit is supersonic, and mass-flow/pressure/Mach errors are independently checked against one-dimensional isentropic theory.

## 4. CFD capability coverage

| Capability | A | B | C | D | E | F |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 2-D flow | ✓ |  | ✓ |  | ✓ | ✓ |
| 3-D flow |  | ✓ |  | ✓ |  |  |
| Laminar viscous flow | ✓ |  | ✓ |  | ✓ | ✓ |
| RANS turbulence / wall treatment |  | ✓ |  | ✓ |  |  |
| Internal flow / pressure loss | ✓ | ✓ |  |  |  | ✓ |
| External aerodynamics / wake |  |  | ✓ | ✓ |  |  |
| Drag / lift / wall shear |  | ✓ | ✓ | ✓ |  |  |
| Energy equation |  |  |  |  | ✓ | ✓ |
| Gravity / buoyancy / Boussinesq |  |  |  |  | ✓ |  |
| Ideal gas / compressibility |  |  |  |  |  | ✓ |
| Transonic / supersonic flow |  |  |  |  |  | ✓ |
| Automated mesh, solve, export, JSON/CSV/SVG | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## 5. Output layout

- Scripts: repository root (`fluent_smoke_common.py`, `fluent_mesh.py`, six case scripts, Phase 0 script, and `run_fluent_smoke_suite.py`).
- Structured results, meshes, raw Fluent exports, processed CSV, SVG, and `.cas.h5/.dat.h5`: `outputs/`.
- Complete console/transcript logs: `logs/fluent_*.log`.
- Each case JSON records model, mesh, results, checks, status, and artifact paths.

## 6. Advanced CFD capabilities not covered

- Transient vortex shedding, spectral lift analysis, and Strouhal extraction.
- LES/DES, transition models, Reynolds-stress models, and detailed y+ grid studies.
- Multiphase, cavitation, VOF, Eulerian, DPM, free-surface, and phase change.
- Species transport, reacting flow, combustion, chemistry, and radiation.
- Conjugate heat transfer, porous media, rotating machinery/MRF/sliding mesh, dynamic mesh, and overset mesh.
- Adaptive mesh refinement, mesh-independence studies, higher-order verification, and uncertainty quantification.
- Density-based solver coverage, real-gas equations of state, shocks with back-pressure sweeps, and hypersonics.
- UDFs, adjoint/optimization, acoustics, GPU solve, distributed HPC scaling, and restart/checkpoint robustness.
