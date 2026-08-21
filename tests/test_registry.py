import json

from agentic_simulation_lab.core.paths import project_root
from agentic_simulation_lab.core.registry import cases


def test_catalog_covers_every_domain():
    catalog = json.loads((project_root() / "benchmarks" / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog["domains"]) == 11
    assert all(domain["cases"] for domain in catalog["domains"])


def test_registry_discovers_cases_and_solvers():
    discovered = cases(project_root())
    assert len(discovered) > 100
    assert {case.domain for case in discovered} == {
        "mechanics", "thermal", "cfd", "multiphysics", "materials",
        "electromagnetics", "acoustics", "porous_geomechanics", "dem", "sph",
        "phase_reactive",
    }
