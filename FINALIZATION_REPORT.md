# Finalization report

Checked: 2026-08-21

Scope: this is a historical snapshot of the pre-integration finalization task, not
the current release-candidate report. Its recorded pytest count and Git state must
not be reused as current evidence. Use `docs/PROJECT_METRICS.md`,
`docs/known-limitations.md`, and exact-revision validation for the current state.

## Project

- Name: Agentic Simulation Lab
- Future public repository: `Charlie-Wang-03/agentic-simulation-lab`
- Package: `agentic-simulation-lab` 0.1.0
- Local absolute paths are intentionally omitted from this public candidate document.

## Catalog (historical finalization snapshot)

The generated catalog contains 11 domains and 134 entries: 123 `PASS`, 4 `FAIL`, 4 `BLOCKED`, and 3 `NOT_RUN`. It contains 113 benchmark entries, 9 dataset generators, and 12 utilities.

## Solver regressions

All selected cases were invoked through the project-local environment and final CLI after successful dry-runs.

| Integration | Case | Result |
|---|---|---:|
| Mechanical/MAPDL | static cantilever | PASS |
| Fluent | laminar channel | PASS |
| AEDT Student | electrostatic capacitor | FAIL |
| Rocky | single-particle free fall | PASS |
| System Coupling | startup/connectivity smoke | PASS |

AEDT official-install discovery and executable trust checks passed, but the supported PyAEDT gRPC session did not start. Cleanup left no AEDT processes. No transport bypass, GUI automation, system setting, or license modification was attempted. Sanitized evidence is in `docs/release/SOLVER_REGRESSION_RESULTS.json`.

## Reactive Case J

The historical corrected Fluent reacting-CHT retest completed after one field-name API fix and one permitted rerun. Seven checks passed, including native reaction, interface creation, solid response, species closure, carbon closure, and mass-flow closure. Its final-step total-enthalpy balance error was 15.951% against the unchanged 10% limit, so the authoritative status remained `FAIL`. A later targeted reliability run, documented outside this snapshot, retained `FAIL` at 15.842% over a fixed window. The initial API failure and final physics failure are both preserved under ignored artifacts.

## Cross-platform

- Windows core commands, static checks, and authorized low-cost solver regressions were exercised locally.
- CI is configured for Windows, macOS, and Ubuntu with Python 3.10 and 3.12 and does not launch proprietary solvers or use license secrets.
- macOS core/package behavior is covered by static CI configuration; macOS solver execution was not locally validated, and local Ansys Student solver execution is not claimed.

## Environment (historical finalization snapshot)

- The project-local `.venv` uses Python 3.12. Its editable installation was repaired during the historical refactor, and all six optional integrations import successfully.
- Optional integrations import successfully for PyMechanical 0.13.2, PyFluent 0.41.0, PyMAPDL 0.74.1, PyAEDT 1.4.0, PyRocky 0.6.1, and PySystemCoupling 0.13.0.
- `tools/bootstrap.py`, optional dependency extras, and `environment.yml` provide reproducible setup without modifying global Python, Conda base, the registry, or system environment variables.
- The wheel and sdist contain no ignored artifacts or proprietary solver formats. A solver-free clean environment installed the wheel with `--no-deps` and passed `list`, `info`, `report`, and `audit`.

## Privacy

- Candidate public-tree privacy scan: PASS
- Secret scan: PASS
- Dataset portability scan: PASS
- Allowed maintainer identifier: `Charlie-Wang-03`
- Other personal identifiers found in the public candidate tree: 0

## Community health

README files, contributing guidance, code of conduct, security and support policies, issue and pull-request templates, CODEOWNERS, changelog, citation metadata, and bilingual installation/publishing tutorials are present. `CITATION.cff` passed CFF 1.2.0 schema validation.

## Compliance

- Current official Ansys and GitHub sources were audited on 2026-08-20.
- The project is independently positioned for education and canonical physics validation and does not claim Ansys endorsement.
- Repository licensing is explicitly separated from Ansys software licensing.
- Public/package scans found no proprietary binaries, solver databases, copied vendor documentation, or redistributable vendor project blobs.
- “Benchmark” is defined as a noncompetitive canonical validation/reference case.

## Static and history validation

- Post-rename Python compile: PASS
- Post-rename pytest: 13/13 PASS
- Post-rename Ruff maintained scope: PASS
- Manifests/catalog/references: PASS
- Historical evidence: 283 JSON and 91 NPZ files PASS with three documented SPH qualifications
- Public tree, privacy, secrets, links, tutorial pairing, subprocess policy, and dataset portability: PASS
- Post-rename package build, archive-content inspection, and solver-free clean-package smoke: PASS

## Public identity

The public software identity is `agentic-simulation-lab`; the private R&D mother repository keeps its historical private identity. The package, CLI, public URLs, and clean export do not depend on the private name. The historical editable-pointer repair and solver-free validation are superseded by the exact-revision evidence produced for the current candidate.

## Git

At the time captured by this historical snapshot, Git was initialized but nothing was staged, committed, pushed, tagged, or connected to a remote. This statement does not describe the later integration-candidate topology. Ignored artifacts and project environments remained local.

## Release gate

**NOT READY FOR PUBLICATION**

Blocking items:

1. Retain or resolve the Case J physics-validation failure without lowering its threshold.
2. Retain or diagnose the AEDT supported-session startup failure without transport or license workarounds.

This historical snapshot predated the approved Apache-2.0 decision and the later release-policy correction. Under the current policy, the truthful Case J and AEDT outcomes remain visible qualifications; they block publication only if their evidence is missing, inconsistent, misleading, private/proprietary, or absent from known limitations.

No public GitHub repository, public push, tag, or release was created.
