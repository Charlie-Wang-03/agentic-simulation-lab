from __future__ import annotations

from collections import Counter
from pathlib import Path

from .registry import cases


def metrics(root: Path | None = None) -> dict[str, object]:
    all_cases = cases(root)
    statuses = Counter(case.status for case in all_cases)
    solvers = Counter(case.solver for case in all_cases)
    roles = Counter(case.role for case in all_cases)
    return {
        "domains": len({case.domain for case in all_cases}),
        "cases": len(all_cases),
        "statuses": dict(sorted(statuses.items())),
        "solver_coverage": dict(sorted(solvers.items())),
        "roles": dict(sorted(roles.items())),
    }
