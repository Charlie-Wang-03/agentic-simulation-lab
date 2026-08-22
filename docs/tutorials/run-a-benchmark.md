# Run a Mechanical benchmark

Confirm the Mechanical optional dependency, installation, and license, then inspect and dry-run the case:

```bash
agentic-sim doctor --probe mechanical
agentic-sim info mechanics static-cantilever
agentic-sim run mechanics --case static-cantilever --dry-run
```

When the product and license are available, remove `--dry-run`. A real run writes its record under `artifacts/runs/mechanics/static-cantilever/` and logs under `artifacts/logs/`. The case compares extracted displacement with beam theory; a zero process exit is necessary but not sufficient.

```bash
agentic-sim validate mechanics --case static-cantilever
```

Inspect `run.json` and the case result together. Report PASS only if the physical checks pass.
