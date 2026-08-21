# Material and Advanced Solid Mechanics Report

Generated: 2026-08-15T12:55:12.799933+00:00
Environment: Windows 11; Ansys Student 2026 R1 / 261; MAPDL batch solver; SI units.

## Executive result

All eight cases were solved by the installed Ansys 261 solver and passed solver-independent physical checks. A solver exit code alone was not accepted: every case has a theory/constitutive comparison and structured finite-data validation.

| Case | Benchmark | Material model | Analysis | Status |
|---|---|---|---|---|
| A | Bilinear plasticity load/unload | TB,PLASTIC,,,,BISO | Nonlinear static | PASS |
| B | Neo-Hookean large-deformation tension | TB,HYPER,,,,NEO | Nonlinear static, NLGEOM=ON | PASS |
| C | Prony stress-relaxation | Generalized Maxwell: TB,PRONY shear + bulk | Small-strain transient | PASS |
| D | Norton secondary creep | TB,CREEP,,,,6 (secondary creep) | Time-dependent static at elevated temperature | PASS |
| E | S-N fatigue with Goodman mean-stress correction | Linear elasticity + project-side S-N curve | Two static extrema; stress-life postprocessing | PASS |
| F | Mode-I center crack SIF | Isotropic linear elastic fracture mechanics | Quarter-symmetry static fracture with CINT SIFS | PASS |
| G | Orthotropic lamina orientation response | 3D orthotropic linear elasticity | Static tension with element material axes | PASS |
| H | Cubic single-crystal directional elasticity | Cubic C11/C12/C44 represented by orthotropic elastic constants | Static tension along [100]/[110]/[111] | PASS |

## Case details

### A — Elastic-plastic load/unload

- Element/mesh: SOLID185, regular 3-D bar (10 nominal elements).
- Model: bilinear isotropic hardening, E=200 GPa, yield=250 MPa, tangent modulus=2 GPa.
- Result: residual strain 0.025; maximum plastic strain 0.025.
- Validation: residual error 1.01%; maximum curve error 1.01%.
- Status: **PASS**.

### B — Hyperelastic large deformation

- Element/mesh: mixed u-P SOLID185; NLGEOM on; maximum stretch 1.5.
- Model: incompressible Neo-Hookean, initial shear modulus 1 MPa.
- Result: maximum force 422.222 N; integrated strain energy 11.6199 J.
- Validation: nominal stress against `mu*(lambda-lambda^-2)`, maximum error 3.82e-06%; energy error 0.401%.
- Status: **PASS**.

### C — Viscoelastic relaxation

- Model: generalized Maxwell/Prony shear and bulk terms; relative relaxing modulus 0.6; tau=2 s.
- Result: 51 time samples; stress relaxed from 100 to 40.4 kPa.
- Validation: exponential relaxation maximum error 0.000153%.
- Status: **PASS**.

### D — Norton creep

- Model: implicit secondary creep `TB,CREEP,,,,6`; temperature 600 °C; constant stress 100 MPa.
- Result: final creep strain 0.001; rate 1e-06 1/s.
- Validation: `epsilon_cr=C1*sigma^n*t`, late-time maximum error 3.33e-05%.
- Status: **PASS**.

### E — Stress-life fatigue

- Structural source: two actual SOLID185 extrema; alternating stress 100 MPa and mean stress 140 MPa.
- Result: Goodman-corrected amplitude 130 MPa; life 1e+07 cycles; damage/cycle 1e-07; 1e6-cycle safety factor 1.57167.
- Load conservation error: 0%.
- Scope note: stress extrema are native MAPDL results; S-N/Goodman life is the documented project-side postprocessor, not a claimed Mechanical Fatigue Tool run.
- Status: **PASS**.

### F — Mode-I fracture

- Crack: center crack quarter-symmetry model; half crack length 0.01 m.
- Tip/mesh: PLANE183 plane stress, `KSCON` quarter-point singular elements, five `CINT` SIFS contours.
- Result: stable-contour mean KI=1.81616 MPa sqrt(m); contour scatter 0.0927%.
- Theory: wide-plate `sigma*sqrt(pi*a)`=1.77245 MPa sqrt(m); error 2.47%.
- Status: **PASS**.

### G — Orthotropic lamina

- Model: 3-D orthotropic elasticity with explicit element material coordinates at 0°, 45°, and 90°.
- Parameters: E1=135 GPa, E2=10 GPa, G12=5 GPa.
- Validation: transformed-compliance formula; maximum direction-modulus error 1.38%.
- Status: **PASS**.

### H — Cubic single-crystal elasticity

- Model: cubic stiffness C11=168, C12=121, C44=75.4 GPa.
- Orientations: [100], [110], [111], using explicitly oriented parallelepipeds and nodal coordinate systems; the material tensor stays in the crystal frame.
- Validation: full compliance-tensor directional modulus; maximum error 6.91e-13%.
- Scope note: elastic anisotropy only; no slip-system crystal plasticity is claimed.
- Status: **PASS**.

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
