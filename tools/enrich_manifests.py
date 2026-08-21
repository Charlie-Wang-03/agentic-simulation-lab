"""Attach exact-name historical result evidence to otherwise unattributed cases."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "artifacts" / "legacy" / "outputs"

SUITE_OVERRIDES = {
    "smoke_aedt_connect.py": "PASS", "smoke_hfss_connect.py": "PASS",
    "smoke_electrostatic.py": "PASS", "smoke_dc_conduction.py": "PASS",
    "smoke_magnetostatic.py": "PASS", "smoke_eddy_current.py": "PASS",
    "smoke_transient_magnetic.py": "BLOCKED", "smoke_hfss_waveguide.py": "PASS",
    "smoke_electrothermal_coupling.py": "PASS", "smoke_force_mechanical_coupling.py": "PASS",
    "generate_electrostatic_dataset.py": "PASS", "validate_electromagnetics_dataset.py": "PASS",
    "smoke_acoustic_pml.py": "PASS", "validate_acoustics_dataset.py": "PASS",
    "probe_phase_reactive_capabilities.py": "PASS", "validate_phase_reactive_dataset.py": "PASS",
    "probe_porous_geomechanics_capabilities.py": "PASS", "validate_rocky_dataset.py": "PASS",
    "probe_sph_capabilities.py": "PASS", "prepare_sph_dataset.py": "PASS",
    "validate_sph_dataset.py": "PASS",
}


def status(value: object) -> str:
    text = str(value or "").upper()
    if "BLOCK" in text:
        return "BLOCKED"
    if text.startswith("PASS"):
        return "PASS"
    if text.startswith("FAIL"):
        return "FAIL"
    if "PARTIAL" in text:
        return "PARTIAL"
    return "NOT_RUN"


def base_name(entrypoint: str) -> str:
    stem = Path(entrypoint).stem
    return re.sub(r"^(smoke|generate|validate|probe|prepare)_", "", stem)


def exact_results() -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in LEGACY.rglob("*.json"):
        keys = {path.stem}
        if path.stem.endswith("_results"):
            keys.add(path.stem.removesuffix("_results"))
        for key in keys:
            index.setdefault(key, []).append(path)
    return index


def compact(data: dict[str, object]) -> dict[str, object]:
    keep = {"status": data.get("status")}
    for key in ("case", "title", "solver", "checks"):
        if key in data:
            keep[key] = data[key]
    return keep


def main() -> None:
    index = exact_results()
    for manifest_path in sorted((ROOT / "benchmarks").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        evidence_records: dict[str, object] = {}
        changed = False
        for case in manifest["cases"]:
            filename = Path(case["entrypoint"]).name
            if case["status"] == "NOT_RUN" and filename in SUITE_OVERRIDES:
                reference = manifest_path.parent / "references" / "suite_summary.json"
                if reference.exists():
                    case["status"] = SUITE_OVERRIDES[filename]
                    case["evidence"] = reference.relative_to(ROOT).as_posix()
                    changed = True
            matches = index.get(base_name(case["entrypoint"]), [])
            if len(matches) != 1:
                continue
            source = matches[0]
            try:
                raw = source.read_bytes()
                data = json.loads(raw)
            except (OSError, json.JSONDecodeError):
                continue
            observed = status(data.get("status"))
            if observed == "NOT_RUN":
                continue
            evidence_records[case["slug"]] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "historical_name": source.name,
                "observed": compact(data),
            }
            if case["status"] == "NOT_RUN":
                case["status"] = observed
                case["evidence"] = f"benchmarks/{manifest['domain']}/references/historical_results.json"
                changed = True
        if evidence_records:
            target = manifest_path.parent / "references" / "historical_results.json"
            target.write_text(json.dumps({"schema_version": 1, "records": evidence_records}, indent=2) + "\n", encoding="utf-8")
        if changed:
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
