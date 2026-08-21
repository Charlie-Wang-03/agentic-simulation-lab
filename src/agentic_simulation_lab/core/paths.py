from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    configured = os.environ.get("AGENTIC_SIMULATION_LAB_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / "benchmarks").is_dir():
            return candidate
    return Path.cwd().resolve()


def artifacts_root(root: Path | None = None) -> Path:
    return (root or project_root()) / "artifacts"
