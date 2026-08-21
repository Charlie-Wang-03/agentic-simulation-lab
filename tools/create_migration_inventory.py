"""Create a reproducible, project-relative migration inventory."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = (
    "mechanics",
    "thermal",
    "cfd",
    "multiphysics",
    "materials",
    "electromagnetics",
    "acoustics",
    "porous_geomechanics",
    "dem",
    "sph",
    "phase_reactive",
)


EXACT_DOMAIN = {
    "smoke_connect.py": "mechanics",
    "smoke_static_cantilever.py": "mechanics",
    "smoke_modal_cantilever.py": "mechanics",
    "smoke_multibody_rigid.py": "mechanics",
    "smoke_multibody_flexible.py": "mechanics",
    "smoke_spring_damper.py": "mechanics",
    "smoke_forced_vibration.py": "mechanics",
    "smoke_joint_drive.py": "mechanics",
    "smoke_contact_friction.py": "mechanics",
    "smoke_impact.py": "mechanics",
    "spaceclaim_multibody_geometry.py": "mechanics",
    "spaceclaim_single_link_geometry.py": "mechanics",
    "smoke_cht_fluent.py": "multiphysics",
    "smoke_cht_system_coupling.py": "multiphysics",
    "smoke_system_coupling_connect.py": "multiphysics",
    "smoke_fsi_one_way.py": "multiphysics",
    "smoke_fsi_two_way.py": "multiphysics",
    "smoke_fsi_turek_hron.py": "multiphysics",
    "smoke_thermo_fsi.py": "multiphysics",
    "smoke_thermal_fluid_structural.py": "multiphysics",
    "smoke_force_mechanical_coupling.py": "multiphysics",
    "smoke_multiphysics_dataset.py": "multiphysics",
    "smoke_electrothermal_coupling.py": "electromagnetics",
    "smoke_thermo_poroelastic.py": "porous_geomechanics",
    "smoke_fluent_melting.py": "phase_reactive",
    "smoke_fluent_natural_convection.py": "cfd",
    "smoke_fluent_acoustics.py": "cfd",
}


PREFIX_DOMAIN = (
    (("smoke_stefan_", "smoke_natural_convection_melting", "smoke_moving_heat_source", "smoke_reaction_diffusion", "smoke_finite_rate_reactor", "smoke_premixed_combustion", "smoke_diffusion_flame", "smoke_combustion_radiation", "smoke_reactive_cht", "smoke_phase_change_dataset", "smoke_reactive_dataset", "probe_phase_reactive", "validate_phase_reactive", "run_phase_reactive", "phase_reactive_"), "phase_reactive"),
    (("smoke_thermal_", "run_thermal_", "thermal_smoke_"), "thermal"),
    (("smoke_fluent_", "run_fluent_", "validate_fluent", "fluent_"), "cfd"),
    (("smoke_plasticity", "smoke_hyperelastic", "smoke_viscoelastic", "smoke_creep", "smoke_fatigue", "smoke_fracture", "smoke_orthotropic", "smoke_single_crystal", "solid_materials_", "run_material_"), "materials"),
    (("smoke_aedt_", "smoke_dc_", "smoke_electrostatic", "smoke_eddy_", "smoke_magnetostatic", "smoke_transient_magnetic", "smoke_hfss_", "generate_electrostatic", "validate_electromagnetics", "run_electromagnetics", "aedt_"), "electromagnetics"),
    (("smoke_acoustic_", "smoke_helmholtz_", "smoke_vibroacoustic_", "acoustics_", "run_acoustics", "validate_acoustics"), "acoustics"),
    (("smoke_darcy_", "smoke_forchheimer_", "smoke_anisotropic_porous", "smoke_porous_", "smoke_geomechanics_", "smoke_geostatic_", "smoke_terzaghi_", "porous_", "probe_porous_", "validate_porous", "run_porous_"), "porous_geomechanics"),
    (("smoke_particle_", "smoke_angle_", "smoke_hopper_", "smoke_rotating_", "smoke_nonspherical_", "smoke_cfd_dem_", "smoke_rocky_", "rocky_", "run_rocky_", "validate_rocky"), "dem"),
    (("smoke_sph_", "sph_", "prepare_sph_", "probe_sph_", "run_sph_", "validate_sph_", "free_surface_sph_"), "sph"),
    (("smoke_cht_", "smoke_fsi_", "smoke_thermo_fsi", "smoke_system_coupling", "smoke_force_mechanical", "smoke_multiphysics", "multiphysics_", "run_multiphysics", "validate_multiphysics"), "multiphysics"),
    (("smoke_static_", "smoke_modal_", "smoke_multibody_", "smoke_spring_", "smoke_forced_", "smoke_joint_", "smoke_contact_", "smoke_impact", "dynamics_smoke_", "spaceclaim_"), "mechanics"),
)


REPORT_DOMAIN = {
    "ACOUSTICS_WAVE_PHYSICS_REPORT.md": "acoustics",
    "CFD_FLUENT_ADVANCED_REPORT.md": "cfd",
    "CFD_FLUENT_FINAL_REPORT.md": "cfd",
    "CFD_FLUENT_SMOKE_REPORT.md": "cfd",
    "ELECTROMAGNETICS_MULTIPHYSICS_REPORT.md": "electromagnetics",
    "MATERIAL_SOLID_MECHANICS_REPORT.md": "materials",
    "MULTIPHYSICS_COUPLING_REPORT.md": "multiphysics",
    "PHASE_CHANGE_REACTIVE_FLOW_REPORT.md": "phase_reactive",
    "POROUS_MEDIA_GEOMECHANICS_REPORT.md": "porous_geomechanics",
    "ROCKY_DEM_CFD_COUPLING_REPORT.md": "dem",
    "SPH_FREE_SURFACE_REPORT.md": "sph",
    "SPH_VOF_COMPARISON.md": "sph",
    "THERMAL_BENCHMARK_REPORT.md": "thermal",
}


def domain_for(path: Path) -> str:
    name = path.name
    if name in EXACT_DOMAIN:
        return EXACT_DOMAIN[name]
    if name in REPORT_DOMAIN:
        return REPORT_DOMAIN[name]
    for prefixes, domain in PREFIX_DOMAIN:
        if name.startswith(prefixes):
            return domain
    return "project"


def target_for(path: Path, domain: str) -> tuple[str, str]:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("outputs/"):
        return f"artifacts/legacy/{rel}", "move"
    if rel.startswith("logs/") or rel == "batch.log":
        return f"artifacts/legacy/{rel}", "move"
    if rel.startswith("__pycache__/") or path.suffix == ".pyc":
        return "(ignored generated cache)", "remove"
    if path.parent == ROOT and path.suffix == ".py":
        stem = path.stem
        if stem.startswith(("run_", "validate_", "probe_", "generate_", "prepare_")):
            leaf = "run_suite.py" if stem.startswith("run_") else f"tools/{name_without_domain(stem, domain)}.py"
        elif stem.endswith(("_common", "_field_export")) or stem in {"fluent_mesh", "fluent_smoke_common", "aedt_smoke_common", "dynamics_smoke_common", "thermal_smoke_common", "solid_materials_common", "multiphysics_common"}:
            leaf = f"common/{stem}.py"
        else:
            leaf = f"cases/{stem.removeprefix('smoke_')}.py"
        return f"benchmarks/{domain}/{leaf}", "move"
    if path.parent == ROOT and path.suffix == ".md" and domain in DOMAINS:
        return f"benchmarks/{domain}/references/{path.name}", "move"
    if rel.startswith("assets/"):
        return f"references/{rel}", "move"
    if rel.startswith(("Ansys/", "nc/")):
        return f"artifacts/legacy/{rel}", "move"
    return rel, "keep/replace"


def name_without_domain(stem: str, domain: str) -> str:
    value = stem
    for token in (f"_{domain}", "_suite"):
        value = value.replace(token, "")
    return value


def main() -> int:
    excluded = {"MIGRATION_INVENTORY.md", "migration_inventory.json"}
    files = [p for p in ROOT.rglob("*") if p.is_file() and p.name not in excluded]
    records = []
    for path in sorted(files):
        rel = path.relative_to(ROOT).as_posix()
        domain = domain_for(path) if path.parent == ROOT else (
            next((d for d in DOMAINS if f"/{d}/" in f"/{rel}/"), "artifacts" if rel.startswith(("outputs/", "logs/")) else "project")
        )
        target, action = target_for(path, domain)
        records.append({"old_path": rel, "bytes": path.stat().st_size, "extension": path.suffix or "(none)",
                        "domain": domain, "target_path": target, "action": action})

    detail = ROOT / "migration_inventory.json"
    detail.write_text(json.dumps({"root_identity": "agentic-simulation-lab", "file_count": len(records),
                                  "total_bytes": sum(r["bytes"] for r in records), "records": records}, indent=2), encoding="utf-8")

    ext = Counter(r["extension"] for r in records)
    domains: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        domains[record["domain"]].append(record)
    sources = [r for r in records if r["old_path"].count("/") == 0 and r["extension"] in {".py", ".md"}]
    lines = [
        "# Migration Inventory",
        "",
        "This project-relative inventory freezes the pre-refactor baseline. The complete per-file map is stored in `migration_inventory.json` and will be archived with the legacy artifacts after migration.",
        "",
        "## Baseline",
        "",
        f"- Files: {len(records)}",
        f"- Bytes: {sum(r['bytes'] for r in records)}",
        f"- Root Python/Markdown sources and reports: {len(sources)}",
        "- Git repository at baseline: no valid `.git` repository",
        "- Historical generated data is preserved and moved, not copied.",
        "",
        "## File types",
        "",
        "| Extension | Count |",
        "|---|---:|",
        *[f"| `{kind}` | {count} |" for kind, count in ext.most_common()],
        "",
        "## Domain inventory",
        "",
        "| Domain | Files | Bytes | Planned root sources |",
        "|---|---:|---:|---:|",
        *[f"| {domain} | {len(items)} | {sum(x['bytes'] for x in items)} | {sum(x in sources for x in items)} |" for domain, items in sorted(domains.items())],
        "",
        "## Root source migration map",
        "",
        "| Old path | Type | Domain | Target | Action |",
        "|---|---|---|---|---|",
        *[f"| `{r['old_path']}` | `{r['extension']}` | {r['domain']} | `{r['target_path']}` | {r['action']} |" for r in sources],
        "",
        "## Artifact migration invariant",
        "",
        "Before moving, `outputs/` and `logs/` counts and byte totals are recorded in the full inventory. After moving, the target trees must have identical file counts and byte totals before the old locations are considered retired.",
    ]
    (ROOT / "MIGRATION_INVENTORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(records), "bytes": sum(r["bytes"] for r in records),
                      "root_sources": len(sources), "inventory": str(detail), "summary": str(ROOT / 'MIGRATION_INVENTORY.md')}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
