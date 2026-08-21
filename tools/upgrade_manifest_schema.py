"""Populate the public manifest contract without changing evidence-derived status."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = {
    "mechanics": ["Mechanical", "MAPDL"], "thermal": ["Mechanical", "MAPDL"],
    "cfd": ["Fluent"], "multiphysics": ["Fluent", "Mechanical", "System Coupling"],
    "materials": ["Mechanical", "MAPDL"], "electromagnetics": ["AEDT"],
    "acoustics": ["Mechanical", "MAPDL", "Fluent"],
    "porous_geomechanics": ["Fluent", "MAPDL"], "dem": ["Rocky"],
    "sph": ["Rocky"], "phase_reactive": ["Fluent", "MAPDL", "reduced-order Python"],
}
PRIMARY = {
    "mechanics": "Mechanical/MAPDL", "thermal": "Mechanical/MAPDL", "cfd": "Fluent",
    "multiphysics": "Fluent/Mechanical/System Coupling", "materials": "Mechanical/MAPDL",
    "electromagnetics": "AEDT", "acoustics": "Mechanical/MAPDL/Fluent",
    "porous_geomechanics": "Fluent/MAPDL", "dem": "Rocky", "sph": "Rocky",
    "phase_reactive": "Fluent/MAPDL/reduced-order Python",
}


def solver_for(domain: str, filename: str) -> str:
    if filename.startswith(("validate_", "prepare_")) or "dataset" in filename:
        return "Python validator/generator"
    if domain == "phase_reactive":
        if filename in {
            "smoke_stefan_phase_change.py", "smoke_moving_heat_source.py",
            "smoke_reaction_diffusion.py", "smoke_phase_change_dataset.py", "smoke_reactive_dataset.py",
        }:
            return "Reduced-order Python"
        if filename.startswith("probe_"):
            return "Fluent/MAPDL"
        return "Fluent"
    if domain == "porous_geomechanics":
        if filename.startswith(("smoke_terzaghi_", "smoke_geostatic_", "smoke_geomechanics_", "smoke_thermo_")):
            return "MAPDL"
        return "Fluent" if filename.startswith("smoke_") else PRIMARY[domain]
    if domain == "multiphysics":
        if "system_coupling" in filename or "fsi" in filename:
            return "Fluent/Mechanical/System Coupling"
        return "Fluent/Mechanical"
    if domain == "electromagnetics":
        return "AEDT"
    if domain == "acoustics":
        return "Fluent" if "fluent" in filename else "MAPDL/Mechanical"
    if domain == "mechanics" and filename.startswith("spaceclaim_"):
        return "SpaceClaim"
    if domain in {"mechanics", "thermal", "materials"}:
        return "Mechanical/MAPDL"
    return PRIMARY[domain]


def main() -> None:
    for path in sorted((ROOT / "benchmarks").glob("*/manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        domain = data["domain"]
        data["required_products"] = PRODUCTS[domain]
        data["runner"] = f"benchmarks/{domain}/run_suite.py"
        for number, case in enumerate(data["cases"], 1):
            case["id"] = f"C{number:03d}"
            case["solver"] = solver_for(domain, Path(case["entrypoint"]).name)
            case["analysis"] = case.get("analysis", case["title"].removeprefix("Smoke "))
            case["reference"] = case.get("evidence")
            case["expected_artifacts"] = ["run.json", "stdout.log", "stderr.log"]
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        counts = Counter(case["status"] for case in data["cases"])
        status_text = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        (path.parent / "README.md").write_text(
            f"# {data['title']}\n\n"
            f"Required product families: {', '.join(data['required_products'])}. "
            f"The manifest currently registers {len(data['cases'])} entries ({status_text}).\n\n"
            f"```bash\nagentic-sim list --domain {domain}\n"
            f"agentic-sim info {domain}\n"
            f"agentic-sim run {domain} --suite --dry-run\n```\n\n"
            "Statuses are evidence-backed and use the project vocabulary. Read `references/suite_summary.json` "
            "for the compact aggregate; generated solver data belongs under `artifacts/`.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
