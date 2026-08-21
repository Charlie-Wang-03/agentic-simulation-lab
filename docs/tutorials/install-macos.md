# macOS installation

The core package supports catalog navigation, manifests, reports, tests, audits, path checks, and dry-runs on macOS. This project does not claim local Ansys Student solver support on macOS.

```bash
python3 tools/bootstrap.py --extras dev
source .venv/bin/activate
agentic-sim list
agentic-sim doctor
agentic-sim run mechanics --case static-cantilever --dry-run
pytest
```

`doctor` must report missing local solver products without a traceback. Some PyAnsys clients can connect to separately licensed remote solvers, but remote licensing and deployment are outside this tutorial. Do not copy Windows Student binaries to macOS or bypass platform/license controls.
