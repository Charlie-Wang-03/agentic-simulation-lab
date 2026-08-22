# Flagship learning path

This path selects eight cases from the larger catalog. Start every level with `info` and `--dry-run`; execute only when the declared product and a valid license are available. Costs are relative educational estimates, not performance guarantees. Every listed status is historical catalog evidence, not a promise for the current machine.

When a level has a representative result PNG, follow the evidence chain in order: benchmark code → solver-result figure → sanitized numeric evidence → referenced validation result. The full 11-domain inventory is in [Real simulation results and provenance](SIMULATION_RESULTS.md).

Level 0 is solver-free orientation:

```bash
agentic-sim list
agentic-sim doctor
agentic-sim list --role dataset
```

## Level 1 — `mechanics/static-cantilever`

- Physics: linear-elastic beam bending and Euler–Bernoulli tip deflection.
- Automation: build, constrain, solve, extract displacement, and compare with an analytical reference.
- Validation: historical tip-displacement relative error; catalog status `PASS`.
- Result evidence: [solved displacement/stress figure](assets/simulations/mechanics/static-cantilever.png) → [sanitized nodal evidence](assets/simulations/mechanics/static-cantilever.evidence.json) → [historical validation record](../benchmarks/mechanics/references/historical_results.json).
- Requirement: domain manifest declares Mechanical and MAPDL; a compatible local product/license is needed to run.
- Cost: low; the preferred first solver-backed case and generally Student-size accessible.

```bash
agentic-sim run mechanics --case static-cantilever --dry-run
agentic-sim run mechanics --case static-cantilever
```

## Level 2A — `thermal/thermal-conduction`

- Physics: steady one-dimensional heat conduction and temperature gradient.
- Automation: thermal material/boundary setup and temperature extraction.
- Validation: comparison with the analytical conduction solution; catalog status `PASS`.
- Result evidence: [temperature field and profile](assets/simulations/thermal/thermal-conduction.png) → [sanitized nodal evidence](assets/simulations/thermal/thermal-conduction.evidence.json) → [historical validation record](../benchmarks/thermal/references/historical_results.json).
- Requirement: Mechanical/MAPDL as declared by the thermal manifest.
- Cost: low; a compact Student-size thermal introduction.

```bash
agentic-sim run thermal --case thermal-conduction --dry-run
agentic-sim run thermal --case thermal-conduction
```

## Level 2B — `thermal/thermal-transient`

- Physics: time-dependent thermal response and physically ordered temperature history.
- Automation: transient stepping, history extraction, and temporal checks.
- Validation: transient analytical/trend checks in the historical result; catalog status `PASS`.
- Requirement: Mechanical/MAPDL as declared by the thermal manifest.
- Cost: low to moderate; more steps and output than steady conduction.

```bash
agentic-sim run thermal --case thermal-transient --dry-run
agentic-sim run thermal --case thermal-transient
```

## Level 3 — `cfd/fluent-laminar-channel`

- Physics: fully developed laminar channel flow and the Poiseuille velocity profile.
- Automation: generate a mesh, configure a steady Fluent solve, and export a profile.
- Validation: velocity-profile, pressure-drop, and mass-flow checks; catalog status `PASS`.
- Requirement: Fluent; the small mesh is intended to remain within Student-scale limits.
- Cost: low for CFD, but includes solver startup.

```bash
agentic-sim run cfd --case fluent-laminar-channel --dry-run
agentic-sim run cfd --case fluent-laminar-channel
```

## Level 4 — `multiphysics/cht-fluent`

- Physics: conjugate heat transfer across coupled fluid and solid regions.
- Automation: multi-region setup, interface handling, field extraction, and conservation accounting.
- Validation: global energy closure and temperature bounds; catalog status `PASS`.
- Result evidence: [fluid–solid temperature/velocity fields](assets/simulations/multiphysics/cht-fluent.png) → [sanitized field evidence](assets/simulations/multiphysics/cht-fluent.evidence.json) → [historical validation record](../benchmarks/multiphysics/references/historical_results.json).
- Requirement: the domain manifest declares Fluent, Mechanical, and System Coupling; inspect the case and local license before execution.
- Cost: moderate; a stronger conservation workflow than the single-physics cases.

```bash
agentic-sim run multiphysics --case cht-fluent --dry-run
agentic-sim run multiphysics --case cht-fluent
```

## Level 5A — `acoustics/acoustic-tube`

- Physics: standing waves in a closed/open acoustic tube and quarter-wave resonance.
- Automation: harmonic MAPDL setup, frequency sweep, axis-field export, and peak detection.
- Validation: resonance frequency against the quarter-wave relation; catalog status `PASS`.
- Requirement: the acoustics domain declares Mechanical, MAPDL, and Fluent; this case uses the MAPDL/Mechanical solver label.
- Cost: moderate; a frequency sweep with richer field output.

```bash
agentic-sim run acoustics --case acoustic-tube --dry-run
agentic-sim run acoustics --case acoustic-tube
```

## Level 5B — `dem/particle-freefall`

- Physics: Lagrangian particle motion under constant gravity.
- Automation: Rocky project construction, transient particle-table export, and trajectory analysis.
- Validation: position and velocity against constant-gravity kinematics; catalog status `PASS`.
- Requirement: Rocky and an applicable license; the case timeout is 300 seconds.
- Cost: moderate, with proprietary solver startup but a very small physical model.

```bash
agentic-sim run dem --case particle-freefall --dry-run
agentic-sim run dem --case particle-freefall
```

## Scientific-AI track — `cfd/fluent-parametric-dataset`

- Physics: steady laminar 2-D lid-driven cavity over 12 Reynolds numbers.
- Automation: parameter sweep, Fluent field export, Dataset Contract v1 writing, checksum/reload validation, and package-level NumPy loading.
- Validation: contract/payload checks remain separate from historical physics evidence; catalog status `PASS`.
- Requirement: Fluent plus the `data` extra for local sample loading.
- Cost: high relative to the learning cases: 12 solves, each requesting up to 900 iterations. It is an educational smoke dataset, not training-scale.

```bash
agentic-sim run cfd --case fluent-parametric-dataset --dry-run
agentic-sim run cfd --case fluent-parametric-dataset
```

Continue with the [dataset tutorial](tutorials/generate-a-dataset.md) to inspect `dataset.json`, load one sample, and run the generic validator. Do not start a solver merely because `doctor` finds an executable; execution still requires explicit intent and a usable license.
