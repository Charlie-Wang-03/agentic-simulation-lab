# Quick Start: discover and diagnose

1. Install the editable project with `python -m pip install -e ".[dev]"`.
2. Run `agentic-sim list` and narrow with `--domain cfd`.
3. Inspect a case with `agentic-sim info cfd fluent-laminar-channel`.
4. Run `agentic-sim doctor`; add `--probe fluent` only when an active probe is authorized.
5. Use `agentic-sim run cfd --case fluent-laminar-channel --dry-run` before consuming a license.
6. Run `agentic-sim validate` and `agentic-sim audit` to check the project contract.

The manifest status is historical evidence, while `doctor` describes the current environment. Neither action launches a solver by default.
