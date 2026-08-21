# Solver support matrix

This table is a historical tested-evidence snapshot. Current package and executable availability comes only from `agentic-sim doctor`; it does not rewrite historical evidence.

| Family | Tested evidence | Python integration | Domains | Known limitation |
|---|---|---|---|---|
| Mechanical / MAPDL | Student 2026 R1 / 261 | PyMechanical 0.13.2; PyMAPDL 0.74.0 | mechanics, thermal, materials, porous, acoustics | Student model-size and core limits apply |
| Fluent | Student 2026 R1 / 261 | PyFluent 0.41.0 | CFD, multiphysics, porous, phase/reactive | Student mesh/core limits apply; chemistry accuracy remains model-dependent |
| AEDT | Electronics Desktop Student 2025 R2 / 252 | PyAEDT 1.4.0 observed in targeted diagnosis | electromagnetics, coupled workflows | default secure-local startup is unavailable for this Student release under the no-transport-fallback policy; Maxwell Transient retains its separate Student limitation |
| System Coupling | 2026 R1 / 261 | PySystemCoupling available | multiphysics | requires installed participant solvers; long FSI is not a release smoke |
| Rocky | Student 2026 R1 / 26.1 | PyRocky 0.4.1 | DEM, SPH | two-way CFD–DEM and selected SPH modes retain explicit API/product blocks |

Support means an adapter and benchmark assets exist; it does not promise availability on every edition. Versions above are historical evidence, not dependency pins or a live environment diagnosis.
