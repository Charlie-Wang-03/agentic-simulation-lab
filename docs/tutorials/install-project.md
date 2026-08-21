# Install the project

Prerequisites: Python 3.10 or newer (CI explicitly covers 3.10 and 3.12), Git if cloning, and enough space for a local virtual environment. Ansys is not required for catalog browsing, dry-runs, tests, or audits.

From the repository root:

```bash
python tools/bootstrap.py --extras dev
```

Activate `.venv` with `.venv\Scripts\Activate.ps1` on PowerShell or `source .venv/bin/activate` on POSIX shells. Then verify:

```bash
agentic-sim list
agentic-sim info mechanics static-cantilever
agentic-sim doctor
agentic-sim audit
```

Install only needed solver extras, for example `python tools/bootstrap.py --extras dev,fluent`. Package installation does not install or license Ansys products.
