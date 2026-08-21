# Porous Media and Geomechanics Report

Generated: 2026-08-16T03:08:34.604291+00:00
Environment: Windows 11; Ansys Student 2026 R1 / 261; PyFluent 0.41.0; PyMAPDL installed; SI units.

## Executive result

The suite contains native Fluent implementations for porous flow/heat/species (A-E), native MAPDL CPT212 implementations for consolidation/geostatic/thermo-poroelasticity (F, G, I), a native MAPDL Mohr-Coulomb plane-strain model (H), and a ten-case CPT212 dataset generator (J). Acceptance is based on analytical laws, conservation, field evolution, or yield criteria—not solver return codes alone.

Current solver preflight: **PASS**.

| Case | Benchmark | Status |
|---|---|---|
| A | Darcy one-dimensional seepage | PASS |
| B | Darcy-Forchheimer nonlinear seepage | PASS |
| C | Anisotropic porous resistance tensor | PASS |
| D | Porous-media heat transfer | PASS |
| E | Porous-media transient species transport | PASS |
| F | Terzaghi one-dimensional consolidation | PASS |
| G | Geostatic initialization and consolidation | PASS |
| H | Nonlinear geomechanical plane-strain compression | PASS |
| I | Thermo-poroelastic three-field coupling | PASS |
| J | Parameterized poromechanics transient dataset | PASS |

## Phase 0 — actual capability check

- Fluent 261 generated settings expose porous activation, porosity, Cartesian viscous/inertial resistance vectors, equilibrium/non-equilibrium thermal controls, and anisotropic species diffusion controls.
- MAPDL 261 documents CPT212/213/215/216/217 with pore-pressure DOFs; CPT212 adds TEMP when KEYOPT(11)=1 and PRES when KEYOPT(12)=1.
- `ANTYPE,SOIL` is the native soil-analysis path. The official VM264 Terzaghi verification also intentionally uses `ANTYPE,STATIC` with physical `TIME`; Case F follows that verified formulation, while Cases G/I exercise `ANTYPE,SOIL`.
- Static settings availability is not reported as a solved PASS. The raw preflight evidence is retained locally under ignored legacy artifacts.

Official references used to pin the APDL formulation: [CPT212 element](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_elem/Hlp_E_CPT212.html), [structural-pore-fluid-diffusion-thermal analysis](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_cou/Hlp_G_COU_porefluiddiffstruct.html), [VM264 input listing](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_vm/Hlp_V_VM264TXT.html), and [porous-media material data](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/ans_mat/elemdatatblpor.html).

## Case summaries and physical acceptance

### A — Darcy one-dimensional seepage

- Solver/model: Fluent, constant-density laminar flow, native porous cell zone; K=1e-8 m2, porosity 0.35, mu=1e-3 Pa s.
- Mesh: structured 80 x 8 quadrilaterals. Theory: `dp/L=mu U/K`.
- Pressure-gradient error: 0.000340732; inferred-permeability error: 0.000340848.
- Status: **PASS**.

### B — Darcy-Forchheimer sweep

- Seven velocities span Darcy-dominated to inertial-loss regimes. Native resistance inputs are D=1e8 1/m2 and C2=2000 1/m.
- Fit: `dp/L=a U+b U2`; a=99963.3, b=999167, R2=1.
- Artifact: `pressure_drop_vs_velocity.csv` and SVG in the Case B output directory.
- Status: **PASS**.

### C — anisotropic permeability

- Native Cartesian resistance stores Kx=1e-8 m2 and Ky=2.5e-9 m2. Isotropic and anisotropic x-flow solves identify Kx; Ky is round-tripped from the native solver zone.
- The equal-x/y-gradient tensor prediction changes the flow angle from 45 to 14.0362 degrees.
- Limitation is explicit: until a solved diagonal-gradient field exists, this is a tensor-setting/identification PASS only if every recorded Case C check passes; it is never presented as a solved diagonal field.
- Status: **PASS**.

### D — porous heat transfer

- Fluent local thermal-equilibrium porous channel with wall heat flux, water-like fluid properties, pressure/velocity/temperature export.
- Energy check compares wall input with `mdot cp (Tout-Tin)`; imbalance=6.27515e-05.
- Status: **PASS**.

### E — porous species transport

- Fluent transient Species Transport step tracer; output includes outlet concentration history and breakthrough curve.
- Checks enforce bounded mass fractions, sum(Yi) near one, downstream propagation, monotonic breakthrough, and t50 against the porous pore-volume residence time `phi L/U` for Fluent's superficial velocity.
- t50=4.5 s; pore-volume estimate=4 s.
- Status: **PASS**.

### F — Terzaghi consolidation (core benchmark)

- MAPDL CPT212, true displacement + pore-pressure diffusion DOFs, single drainage, plane strain, top load. K is hydraulic conductivity in m/s, matching MAPDL `TB,PM,,,,PERM` units.
- Mesh/time: 20 CPT212 elements; 100 substeps to 0.02 s.
- Multiple Tv values compare pore-pressure profiles, average degree of consolidation, and settlement against the Terzaghi Fourier series.
- Maximum profile error=0.02162; maximum degree error=0.0136743.
- Status: **PASS**.

### G — geostatic initialization plus consolidation

- MAPDL `ANTYPE,SOIL`, CPT212, solid/fluid specific weights, initial hydrostatic pore pressure, gravity/self-weight stage, then added surface load.
- Checks cover hydrostatic pressure, stress growth with depth, bulk-weight stress scale, generated/dissipating excess pressure, and developing settlement.
- Initial/final excess pressure=36234 / 82.31 Pa.
- Limitation: the prescribed hydrostatic field is released after initialization; without a sustained pore-fluid gravity term, the consolidation stage drains toward the zero-pressure datum.
- Status: **PASS**.

### H — nonlinear geomechanics

- MAPDL PLANE182 plane strain with native Mohr-Coulomb `TB,MC`, cohesion 20 kPa, friction 30 degrees, dilation 5 degrees, and 50 kPa lateral confinement.
- Axial stress-strain, volumetric strain and equivalent plastic strain are compared with the Mohr-Coulomb compression meridian. The comparison uses an explicit 18% engineering tolerance because plane-strain confinement adds out-of-plane stress.
- Yield error=0.0144353.
- Status: **PASS**.

### I — thermo-poroelasticity

- CPT212 KEYOPT(11)=1 and KEYOPT(12)=1, `ANTYPE,SOIL`, thermal conductivity/capacity, solid/fluid expansion, drained heated column.
- Acceptance requires simultaneously nontrivial finite temperature, pore pressure, and displacement fields; not merely three declared DOFs.
- Temperature range=22.4189 K; max pore pressure=0.330303 Pa; max displacement=0.0146768 m.
- Status: **PASS**.

### J — Neural Operator / ROM dataset

- Ten native CPT212 parameter cases vary permeability, porosity, modulus and load. Each NPZ stores coordinates, connectivity, common time samples, pore pressure `[time,node]`, displacement `[time,node,component]`, stress and effective stress plus JSON metadata/global responses.
- Completed cases=10 / 10.
- `validate_porous_dataset.py` checks case count, shapes, time order, finiteness, units, parameter metadata and pressure-dissipation direction.
- Status: **PASS**.

## Output organization

- Results: `outputs/porous_geomechanics/<case>/`
- Logs: `logs/porous_geomechanics/`
- Fluent fields: coordinates, pressure, velocity, temperature/species where applicable, with porous parameters in metadata.
- MAPDL fields: coordinates, connectivity, pore pressure, displacement, stress, effective stress, and temperature where applicable.
- Transient convention: scalar `field[time,node]`; vectors/tensors append a component axis.

## Capability matrix

| Capability | Evidence | Status |
|---|---|---|
| Darcy flow | Case A | PASS |
| Forchheimer flow | Case B | PASS |
| isotropic porous media | Case A | PASS |
| anisotropic porous media | Case C | PASS |
| porous heat transfer | Case D | PASS |
| porous species transport | Case E | PASS |
| pore-pressure diffusion | Case F | PASS |
| poroelasticity | Case F | PASS |
| consolidation | Case F | PASS |
| geostatic initialization | Case G | PASS |
| nonlinear soil / rock mechanics | Case H | PASS |
| thermo-poroelasticity | Case I | PASS |
| poromechanics transient dataset | Case J | PASS |

## Current blocking evidence

If the preflight is license-blocked, Fluent's transcript contains `Cannot initialize ANSYS Licensing context` and MAPDL's solver output contains `ANSYS LICENSE MANAGER ERROR`. This is recorded as **BLOCKED** (current license context), not mislabelled as a Student feature limit or API absence. Re-running the unified suite after licensing recovers will execute all cases and replace the effective statuses with physical PASS/FAIL results.

## Deferred directions

Unsaturated/Richards flow; multiphase porous flow; groundwater free surface; fractured media and hydraulic fracturing; reservoir simulation; soil-structure interaction; liquefaction; seepage failure; slopes/tunnels; granular DEM and CFD-DEM; reactive porous transport.
