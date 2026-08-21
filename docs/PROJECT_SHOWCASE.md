# Showcase

Use `agentic-sim list` to browse the full laboratory and `info` to inspect evidence. The examples below are historical, solver-backed PASS results; they illustrate the validation style rather than guaranteeing identical results elsewhere.

| Area | Problem and solver | Agent workflow | Physical validation | Key historical result |
|---|---|---|---|---|
| Mechanics | 3-D static cantilever, Mechanical/MAPDL | build SOLID186 beam → solve → extract tip displacement | Euler–Bernoulli tip deflection | 0.100143 mm vs 0.100000 mm; 0.143% error |
| CFD | 2-D laminar channel, Fluent | mesh → steady solve → export profile | Poiseuille profile, pressure drop, mass flow | profile L2 error 0.210%; pressure-drop error 0.150% |
| Multiphysics | fluid-solid CHT, Fluent | conformal fluid/solid setup → solve → integrate fluxes | global energy closure and temperature bounds | 0.900% energy imbalance |
| Electromagnetics | parallel-plate electrostatics, AEDT | discover Student runtime → solve → extract matrix/field | capacitance and uniform-field theory | capacitance 10.472 pF; mean field 100.0003 V/m |
| Acoustics | closed/open standing-wave tube, MAPDL | harmonic sweep → axis export → peak detection | quarter-wave frequency | 86.0 Hz vs 85.81 Hz; 0.221% error |
| DEM | single-particle free fall, Rocky | run transient → export particle trajectory | constant-gravity kinematics | max position error 1.34 µm; velocity error below 1e-12 m/s |

DEM/SPH evidence also includes dam-break, sloshing, jet-impact, and rigid-body cases with explicit qualifications for masked Eulerian cells. See the domain reports and `benchmarks/*/references/` for compact source records.
