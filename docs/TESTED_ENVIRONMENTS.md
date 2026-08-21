# Tested environments

Checked: 2026-08-21

| Environment | Status | Scope |
|---|---|---|
| Windows 11, Python 3.12 | Locally tested | Core imports, CLI, manifests, catalog, tests, static audits |
| Project-local `.venv`, Python 3.12 | Locally tested after final rename | Editable environment; all six optional client imports and current `doctor` diagnosis pass. |
| Ansys Student 2026 R1 / 261 | Historical and targeted solver evidence | Mechanical/MAPDL, Fluent, System Coupling, Rocky; Case J fresh fixed-window evidence truthfully remains `FAIL` |
| Ansys Electronics Desktop Student 2025 R2 / 252 | Historical `FAIL`; fresh static compatibility diagnosis `BLOCKED` | AEDT electrostatics historical status is not overwritten; fresh diagnosis stopped before session startup and launched no solver |
| macOS GitHub-hosted runner | Workflow configured; actual run evidence tracked separately | Core install, imports, CLI, tests, paths, manifests, audits; configuration alone is not a remote PASS and no local solver claim is made |

Optional solver dependencies are extras in `pyproject.toml`; the core has no mandatory solver package. Use `python tools/bootstrap.py --extras dev` for static development or name the required extras, such as `--extras dev,fluent`. Solver software and licenses are always separate.

Observed project-environment client versions: PyMechanical 0.13.2, PyFluent 0.41.0, PyMAPDL 0.74.1, PyAEDT 1.4.0, PyRocky 0.6.1, and PySystemCoupling 0.13.0. These are environment observations, not dependency pins or solver compatibility guarantees.
