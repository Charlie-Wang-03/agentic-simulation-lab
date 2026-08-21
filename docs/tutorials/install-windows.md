# Windows installation

1. Install a supported 64-bit Python from a trusted source and enable the Python launcher.
2. Clone or extract this repository into a normal user-writable project folder. Do not place it inside an Ansys installation.
3. Open PowerShell in the repository root and run `py -3.12 tools/bootstrap.py --extras dev`.
4. Activate with `.venv\Scripts\Activate.ps1` and run `agentic-sim doctor`.
5. Before any licensed run, inspect the case and use `--dry-run`.

Execution policy may prevent PowerShell activation scripts. In that case, call `.venv\Scripts\python.exe` directly; do not weaken machine-wide security policy. Optional Ansys software is installed separately by its official installer and governed by its own license.
