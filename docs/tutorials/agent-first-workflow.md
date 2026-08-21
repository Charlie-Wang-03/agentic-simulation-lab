# Agent-first workflow

A traditional GUI workflow hides state in clicks and project files. The agent-first path makes intent and evidence explicit:

```text
human intent → manifest discovery → agent reasoning → CLI execution → solver → physics validation → artifacts
```

The agent orchestrates; it does not replace the numerical solver or engineering judgment. Begin with `agentic-sim list`, inspect with `info`, diagnose with `doctor`, and dry-run the exact command. Only then authorize a solver run. Read the numerical checks and preserve failures as useful evidence.
