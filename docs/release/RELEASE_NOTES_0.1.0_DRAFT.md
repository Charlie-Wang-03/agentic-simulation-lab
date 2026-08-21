# Agentic Simulation Lab 0.1.0 — draft release notes

Status: draft only; repository publication preparation is authorized, but no tag, PyPI, Zenodo, or release publication is authorized yet.

## Scope

- 11 manifest-driven physics domains and 134 catalog entries: 123 `PASS`, 4 `FAIL`, 4 `BLOCKED`, and 3 `NOT_RUN`.
- Solver-independent Python package and `agentic-sim` CLI for discovery, diagnostics, dry-runs, validation, reports, and public-tree audits.
- Optional Mechanical/MAPDL, Fluent, AEDT, Rocky, and System Coupling integrations with generated artifacts kept outside the public candidate tree.
- Canonical physics checks using analytical solutions, conservation, reload validation, and expected trends.
- English and Simplified Chinese onboarding and installation guidance.

## Known limitations

- Ansys software and licenses are not included. Student products have platform, use, model-size, core, and feature limits.
- Windows is the locally tested solver platform. macOS supports the core package and static workflows; local Ansys Student solver execution is not claimed.
- Case G premixed combustion, the historical Turek–Hron FSI case, corrected Case J, and the current AEDT electrostatic regression remain explicit `FAIL` evidence.
- Mechanical/MAPDL, Fluent, Rocky, and System Coupling representative regressions pass. AEDT official discovery passes, but its supported PyAEDT gRPC session fails to start.
- Repository-owned content is licensed under Apache-2.0. This does not license Ansys software or erase the truthful `FAIL`, `BLOCKED`, and `NOT_RUN` limitations above.
