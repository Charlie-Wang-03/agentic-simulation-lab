# Project vision

## Problem

Engineering simulation is frequently GUI-heavy, difficult to reproduce, difficult to automate, hard to audit, and inconvenient for coding agents. A solver project can contain valuable physics while still lacking a stable interface for discovery, validation, and dataset generation.

## Proposed paradigm

```text
human intent → agent reasoning → executable simulation → solver → physics validation → evidence
```

Agentic Simulation Lab makes that chain explicit through manifests, a unified CLI, solver-local implementations, and compact references. An agent can inspect what a case means before execution, while a human retains control over authorization, model choices, thresholds, and interpretation.

The agent does not replace the solver. The agent does not replace physical validation. It orchestrates them, records what happened, and makes failures useful rather than hiding them. Product availability, license limits, numerical assumptions, and reduced-order provenance remain visible.
