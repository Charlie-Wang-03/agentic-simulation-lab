"""One-time, deterministic migration into the agentic-simulation-lab layout.

The operation is intentionally idempotent. It moves (never copies) the large
legacy artifact trees and emits a machine-readable migration receipt.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = (
    "mechanics", "thermal", "cfd", "multiphysics", "materials",
    "electromagnetics", "acoustics", "porous_geomechanics", "dem", "sph",
    "phase_reactive",
)

EXACT = {
    "smoke_connect.py": "mechanics",
    "dynamics_smoke_common.py": "mechanics",
    "solid_materials_common.py": "materials",
    "thermal_smoke_common.py": "thermal",
    "fluent_smoke_common.py": "cfd", "fluent_mesh.py": "cfd",
    "fluent_field_export.py": "cfd",
    "multiphysics_common.py": "multiphysics",
    "multiphysics_field_export.py": "multiphysics",
    "aedt_smoke_common.py": "electromagnetics",
    "acoustics_common.py": "acoustics", "acoustics_field_export.py": "acoustics",
    "porous_geomechanics_common.py": "porous_geomechanics",
    "porous_field_export.py": "porous_geomechanics",
    "rocky_smoke_common.py": "dem", "rocky_field_export.py": "dem",
    "free_surface_sph_common.py": "sph", "sph_field_export.py": "sph",
    "phase_reactive_common.py": "phase_reactive",
    "phase_reactive_field_export.py": "phase_reactive",
}

PREFIXES = (
    ("smoke_fluent_melting", "phase_reactive"),
    ("smoke_sph_", "sph"), ("prepare_sph_", "sph"), ("probe_sph_", "sph"),
    ("validate_sph_", "sph"), ("run_sph_", "sph"),
    ("smoke_particle_", "dem"), ("smoke_angle_", "dem"),
    ("smoke_hopper_", "dem"), ("smoke_rotating_", "dem"),
    ("smoke_nonspherical_", "dem"), ("smoke_cfd_dem_", "dem"),
    ("smoke_rocky_", "dem"), ("validate_rocky_", "dem"), ("run_rocky_", "dem"),
    ("smoke_acoustic_", "acoustics"), ("smoke_helmholtz_", "acoustics"),
    ("smoke_vibroacoustic_", "acoustics"), ("validate_acoustics_", "acoustics"),
    ("run_acoustics_", "acoustics"),
    ("smoke_darcy_", "porous_geomechanics"), ("smoke_forchheimer_", "porous_geomechanics"),
    ("smoke_anisotropic_", "porous_geomechanics"), ("smoke_porous_", "porous_geomechanics"),
    ("smoke_terzaghi_", "porous_geomechanics"), ("smoke_geostatic_", "porous_geomechanics"),
    ("smoke_geomechanics_", "porous_geomechanics"), ("smoke_thermo_poroelastic", "porous_geomechanics"),
    ("probe_porous_", "porous_geomechanics"), ("validate_porous_", "porous_geomechanics"),
    ("run_porous_", "porous_geomechanics"),
    ("smoke_aedt_", "electromagnetics"), ("smoke_hfss_", "electromagnetics"),
    ("smoke_electrostatic", "electromagnetics"), ("smoke_dc_", "electromagnetics"),
    ("smoke_magnetostatic", "electromagnetics"), ("smoke_eddy_", "electromagnetics"),
    ("smoke_transient_magnetic", "electromagnetics"), ("smoke_electrothermal_", "electromagnetics"),
    ("smoke_force_mechanical_", "electromagnetics"), ("generate_electrostatic_", "electromagnetics"),
    ("validate_electromagnetics_", "electromagnetics"), ("run_electromagnetics_", "electromagnetics"),
    ("smoke_fluent_", "cfd"), ("validate_fluent_", "cfd"), ("run_fluent_", "cfd"),
    ("smoke_cht_", "multiphysics"), ("smoke_fsi_", "multiphysics"),
    ("smoke_thermal_fluid_", "multiphysics"), ("smoke_thermo_fsi", "multiphysics"),
    ("smoke_multiphysics_", "multiphysics"), ("smoke_system_coupling_", "multiphysics"),
    ("validate_multiphysics_", "multiphysics"), ("run_multiphysics_", "multiphysics"),
    ("smoke_plasticity", "materials"), ("smoke_hyperelastic", "materials"),
    ("smoke_viscoelastic", "materials"), ("smoke_creep", "materials"),
    ("smoke_fatigue", "materials"), ("smoke_fracture", "materials"),
    ("smoke_orthotropic", "materials"), ("smoke_single_crystal", "materials"),
    ("run_material_", "materials"),
    ("smoke_thermal_", "thermal"), ("run_thermal_", "thermal"),
    ("probe_phase_", "phase_reactive"), ("validate_phase_", "phase_reactive"),
    ("run_phase_", "phase_reactive"), ("smoke_stefan_", "phase_reactive"),
    ("smoke_natural_convection_melting", "phase_reactive"),
    ("smoke_moving_heat_source", "phase_reactive"), ("smoke_reaction_diffusion", "phase_reactive"),
    ("smoke_finite_rate_", "phase_reactive"), ("smoke_premixed_", "phase_reactive"),
    ("smoke_diffusion_flame", "phase_reactive"), ("smoke_combustion_", "phase_reactive"),
    ("smoke_reactive_", "phase_reactive"), ("smoke_phase_change_", "phase_reactive"),
    ("smoke_fluent_melting", "phase_reactive"),
    ("smoke_static_", "mechanics"), ("smoke_modal_", "mechanics"),
    ("smoke_contact_", "mechanics"), ("smoke_spring_", "mechanics"),
    ("smoke_forced_", "mechanics"), ("smoke_impact", "mechanics"),
    ("smoke_joint_", "mechanics"), ("smoke_multibody_", "mechanics"),
    ("spaceclaim_", "mechanics"),
)

REPORTS = {
    "ACOUSTICS_WAVE_PHYSICS_REPORT.md": "acoustics",
    "CFD_FLUENT_ADVANCED_REPORT.md": "cfd", "CFD_FLUENT_FINAL_REPORT.md": "cfd",
    "CFD_FLUENT_SMOKE_REPORT.md": "cfd", "ELECTROMAGNETICS_MULTIPHYSICS_REPORT.md": "electromagnetics",
    "MATERIAL_SOLID_MECHANICS_REPORT.md": "materials", "MULTIPHYSICS_COUPLING_REPORT.md": "multiphysics",
    "PHASE_CHANGE_REACTIVE_FLOW_REPORT.md": "phase_reactive",
    "POROUS_MEDIA_GEOMECHANICS_REPORT.md": "porous_geomechanics",
    "ROCKY_DEM_CFD_COUPLING_REPORT.md": "dem", "SPH_FREE_SURFACE_REPORT.md": "sph",
    "SPH_VOF_COMPARISON.md": "sph", "THERMAL_BENCHMARK_REPORT.md": "thermal",
}

SUMMARY_DIR = {
    "acoustics": "acoustics", "electromagnetics": "electromagnetics",
    "materials": "materials", "phase_reactive": "phase_reactive",
    "porous_geomechanics": "porous_geomechanics", "rocky_dem": "dem",
    "sph_free_surface": "sph",
}

def domain_for(name: str) -> str | None:
    if name in EXACT:
        return EXACT[name]
    return next((domain for prefix, domain in PREFIXES if name.startswith(prefix)), None)

def slug(stem: str) -> str:
    return re.sub(r"^(smoke|generate|validate|probe|prepare)_", "", stem).replace("_", "-")

def normalized_status(value: object) -> str:
    text = str(value or "NOT_RUN").upper()
    if "BLOCK" in text:
        return "BLOCKED"
    if text.startswith("PASS"):
        return "PASS"
    if text.startswith("FAIL"):
        return "FAIL"
    if "PARTIAL" in text:
        return "PARTIAL"
    return "NOT_RUN"

def sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        replaced = value.replace(str(ROOT) + "\\", "").replace(str(ROOT) + "/", "")
        return replaced.replace("\\", "/")
    return value

def historical_statuses() -> dict[str, str]:
    result: dict[str, str] = {}
    source = ROOT / "outputs"
    if not source.exists():
        source = ROOT / "artifacts" / "legacy" / "outputs"
    for summary in source.glob("*/suite_summary.json"):
        try:
            data = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read historical summary {summary}") from exc
        cases = data.get("cases", data.get("statuses", {}))
        if isinstance(cases, dict):
            by_label = {str(k): (v.get("status") if isinstance(v, dict) else v) for k, v in cases.items()}
        else:
            by_label = {str(v.get("case")): v.get("status") for v in cases if isinstance(v, dict)}
        for run in data.get("runs", []):
            if isinstance(run, dict) and run.get("script"):
                result[run["script"]] = normalized_status(by_label.get(str(run.get("case"))))
        # Remaining suite mappings are recovered from runner source literals.
        domain = SUMMARY_DIR.get(summary.parent.name)
        if domain:
            runner = next(iter(ROOT.glob(f"run_{summary.parent.name}*_suite.py")), None)
            if runner:
                text = runner.read_text(encoding="utf-8")
                for label, script in re.findall(r'[\(\[]\s*"([A-Z]|Phase 0)"\s*,(?:\s*"[^"]+"\s*,)?\s*"([^"]+\.py)"', text):
                    result[script] = normalized_status(by_label.get(label))
    return result

def count_tree(path: Path) -> tuple[int, int]:
    files = [p for p in path.rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)

def main() -> None:
    statuses = historical_statuses()
    receipt: dict[str, object] = {"public_name": "agentic-simulation-lab", "moves": [], "artifact_moves": {}}
    for domain in DOMAINS:
        base = ROOT / "benchmarks" / domain
        for child in ("cases", "common", "references"):
            (base / child).mkdir(parents=True, exist_ok=True)

    for path in sorted(ROOT.glob("*.py")):
        domain = domain_for(path.name)
        if not domain:
            continue
        kind = "common" if path.name in EXACT and ("common" in path.name or "field_export" in path.name or path.name == "fluent_mesh.py") else "cases"
        if path.name.startswith("run_"):
            target = ROOT / "benchmarks" / domain / "legacy_suite.py"
        else:
            target = ROOT / "benchmarks" / domain / kind / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            path.unlink()
        else:
            shutil.move(str(path), str(target))
        receipt["moves"].append({"from": path.name, "to": target.relative_to(ROOT).as_posix()})

    reports = ROOT / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    for name, domain in REPORTS.items():
        source = ROOT / name
        target = reports / domain / name.lower()
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists() and not target.exists():
            shutil.move(str(source), str(target))

    legacy_outputs = ROOT / "outputs"
    for old_name, domain in SUMMARY_DIR.items():
        summary = legacy_outputs / old_name / "suite_summary.json"
        if summary.exists():
            data = sanitize(json.loads(summary.read_text(encoding="utf-8")))
            target = ROOT / "benchmarks" / domain / "references" / "suite_summary.json"
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for domain in DOMAINS:
        base = ROOT / "benchmarks" / domain
        cases = []
        for path in sorted((base / "cases").glob("*.py")):
            if path.name.startswith(("validate_", "probe_", "prepare_")):
                role = "utility"
            elif path.name.startswith("generate_") or "dataset" in path.name:
                role = "dataset"
            else:
                role = "benchmark"
            cases.append({
                "slug": slug(path.stem), "title": path.stem.replace("_", " ").title(),
                "entrypoint": path.relative_to(ROOT).as_posix(), "role": role,
                "status": statuses.get(path.name, "NOT_RUN"),
                "evidence": f"benchmarks/{domain}/references/suite_summary.json" if statuses.get(path.name) else None,
            })
        manifest = {"schema_version": 1, "domain": domain, "title": domain.replace("_", " ").title(), "cases": cases}
        (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (base / "README.md").write_text(
            f"# {manifest['title']}\n\nSolver-backed benchmarks and validation assets. Status values come from `manifest.json`; `NOT_RUN` means no attributable historical suite evidence was found.\n",
            encoding="utf-8",
        )
        (base / "run_suite.py").write_text(
            f"from agentic_simulation_lab.cli import main\n\nif __name__ == '__main__':\n    raise SystemExit(main(['run', '{domain}', '--suite']))\n",
            encoding="utf-8",
        )

    artifacts = ROOT / "artifacts" / "legacy"
    artifacts.mkdir(parents=True, exist_ok=True)
    for name in ("outputs", "logs"):
        source, target = ROOT / name, artifacts / name
        if source.exists():
            before = count_tree(source)
            shutil.move(str(source), str(target))
            after = count_tree(target)
            if before != after:
                raise RuntimeError(f"artifact count mismatch for {name}: {before} != {after}")
            receipt["artifact_moves"][name] = {"files": after[0], "bytes": after[1]}
    for name in ("batch.log", "migration_inventory.json"):
        source = ROOT / name
        if source.exists():
            shutil.move(str(source), str(artifacts / name))

    (ROOT / "migration_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
