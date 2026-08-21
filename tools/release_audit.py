"""Generate a machine-readable publication-readiness decision."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import platform
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_simulation_lab.cli import main as cli_main
from agentic_simulation_lab.core.audit import (
    APACHE_2_LICENSE_SHA256,
    audit,
    audit_release_metadata,
    audit_source_provenance,
)
from agentic_simulation_lab.core.registry import cases as catalog_cases
from agentic_simulation_lab.core.release_policy import evidence_integrity_gate
from agentic_simulation_lab.core.validation import validate_project

GATE_STATUSES = {"PASS", "FAIL", "BLOCKED"}
CASE_STATUSES = {"PASS", "FAIL", "BLOCKED", "PARTIAL", "NOT_RUN"}
REPRESENTATIVE = {
    "mechanical_mapdl": ("mechanics", "static-cantilever"),
    "fluent": ("cfd", "fluent-laminar-channel"),
    "aedt": ("electromagnetics", "electrostatic"),
    "rocky": ("dem", "particle-freefall"),
    "system_coupling": ("multiphysics", "system-coupling-connect"),
}


def command_status(command: list[str], timeout: int = 300) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "FAIL", f"{type(exc).__name__}: {exc}"
    detail = (completed.stdout + completed.stderr).strip()[-2000:]
    return ("PASS" if completed.returncode == 0 else "FAIL"), detail


def latest_run(domain: str, case: str) -> dict[str, object] | None:
    records = sorted((ROOT / "artifacts" / "runs" / domain / case).glob("*/run.json"))
    if not records:
        return None
    try:
        return json.loads(records[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "FAIL", "error": "latest run record is unreadable"}


def structural_gate(paths: list[str]) -> dict[str, object]:
    missing = [path for path in paths if not (ROOT / path).is_file()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing}


def package_gate(generated_at: datetime) -> dict[str, object]:
    """Build, inspect, install, and smoke-test packages without solver dependencies."""
    stamp = generated_at.strftime("%Y%m%dT%H%M%S%fZ")
    package_root = ROOT / "artifacts" / "release" / f"package-{stamp}"
    dist_dir = package_root / "dist"
    build_status, build_detail = command_status(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist_dir)]
    )
    if build_status != "PASS":
        return {"status": "FAIL", "stage": "build", "detail": build_detail}

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    errors: list[str] = []
    if len(wheels) != 1 or len(sdists) != 1:
        errors.append(f"expected one wheel and one sdist; found {len(wheels)} wheel(s), {len(sdists)} sdist(s)")
        return {"status": "FAIL", "stage": "archive-selection", "errors": errors}
    wheel = wheels[0]
    sdist = sdists[0]

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        wheel_license_names = [name for name in wheel_names if name.endswith(".dist-info/licenses/LICENSE")]
        wheel_license_hashes = [hashlib.sha256(archive.read(name)).hexdigest() for name in wheel_license_names]
        metadata_names = [name for name in wheel_names if name.endswith(".dist-info/METADATA")]
        metadata = archive.read(metadata_names[0]).decode("utf-8") if len(metadata_names) == 1 else ""
        wheel_payload = b"\n".join(archive.read(name) for name in wheel_names if not name.endswith("/"))
    with tarfile.open(sdist) as archive:
        sdist_members = archive.getmembers()
        sdist_license_members = [member for member in sdist_members if member.isfile() and member.name.endswith("/LICENSE")]
        sdist_license_hashes = [
            hashlib.sha256(archive.extractfile(member).read()).hexdigest()  # type: ignore[union-attr]
            for member in sdist_license_members
        ]
        sdist_payload = b"\n".join(
            archive.extractfile(member).read()  # type: ignore[union-attr]
            for member in sdist_members
            if member.isfile()
        )

    if wheel_license_hashes != [APACHE_2_LICENSE_SHA256]:
        errors.append(f"wheel Apache-2.0 license mismatch: {wheel_license_hashes}")
    if sdist_license_hashes != [APACHE_2_LICENSE_SHA256]:
        errors.append(f"sdist Apache-2.0 license mismatch: {sdist_license_hashes}")
    for declaration in ("Name: agentic-simulation-lab", "License-Expression: Apache-2.0", "License-File: LICENSE"):
        if declaration not in metadata:
            errors.append(f"wheel metadata missing {declaration}")
    prohibited_markers = (
        b"agentic_" + b"ansys_lab",
        b"agentic-" + b"ansys-lab",
        b"Charlie-Wang-03/agentic-" + b"ansys-lab",
        b"D:\\simulation_files",
    )
    for marker in prohibited_markers:
        if marker in wheel_payload or marker in sdist_payload:
            errors.append(f"package contains prohibited marker {marker.decode(errors='replace')}")
    if any("/artifacts/" in f"/{name}" for name in wheel_names):
        errors.append("wheel contains artifacts")
    if any("/artifacts/" in f"/{member.name}" for member in sdist_members):
        errors.append("sdist contains artifacts")
    if errors:
        return {"status": "FAIL", "stage": "archive-inspection", "errors": errors}

    install_dir = package_root / "install"
    install_status, install_detail = command_status(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(install_dir), str(wheel)]
    )
    if install_status != "PASS":
        return {"status": "FAIL", "stage": "isolated-install", "detail": install_detail}
    smoke_code = (
        "import sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "import agentic_simulation_lab; "
        "from agentic_simulation_lab.cli import main; "
        "assert not any(name == 'ansys' or name.startswith('ansys.') for name in sys.modules); "
        "raise SystemExit(main(['list', '--domain', 'mechanics']))"
    )
    smoke_status, smoke_detail = command_status([sys.executable, "-I", "-c", smoke_code, str(install_dir)])
    return {
        "status": smoke_status,
        "stage": "complete" if smoke_status == "PASS" else "isolated-smoke",
        "wheel": {
            "name": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "file_count": len(wheel_names),
        },
        "sdist": {
            "name": sdist.name,
            "sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
            "file_count": len(sdist_members),
        },
        "license_sha256": APACHE_2_LICENSE_SHA256,
        "detail": smoke_detail,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-static", action="store_true", help="run pytest and Ruff as part of this audit")
    parser.add_argument("--run-package", action="store_true", help="build, inspect, install, and smoke-test packages")
    args = parser.parse_args(argv)
    generated_at = datetime.now(timezone.utc)

    provenance_errors = audit_source_provenance(ROOT)
    public_errors = validate_project(ROOT) + audit(ROOT) + provenance_errors
    privacy_markers = ("private", "forbidden", "email")
    secret_markers = ("secret",)
    privacy_errors = [item for item in public_errors if any(marker in item.lower() for marker in privacy_markers)]
    secret_errors = [item for item in public_errors if any(marker in item.lower() for marker in secret_markers)]

    gates: dict[str, dict[str, object]] = {}
    if args.run_static:
        pytest_temp = ROOT / "artifacts" / "release" / f"pytest-temp-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}"
        pytest_temp.parent.mkdir(parents=True, exist_ok=True)
        tests_status, tests_detail = command_status(
            [sys.executable, "-m", "pytest", "-q", "--basetemp", str(pytest_temp)]
        )
        ruff_status, ruff_detail = command_status(
            [
                sys.executable, "-m", "ruff", "check", "src", "tests", "tools",
                "--no-cache",
                "benchmarks/phase_reactive/cases/smoke_reactive_cht.py",
                "benchmarks/phase_reactive/common/energy_accounting.py",
                "benchmarks/electromagnetics/common/aedt_diagnostics.py",
                "benchmarks/electromagnetics/common/aedt_smoke_common.py",
                "benchmarks/electromagnetics/cases/smoke_aedt_connect.py",
                "benchmarks/electromagnetics/cases/smoke_hfss_connect.py",
            ]
        )
        gates["tests"] = {"status": tests_status, "detail": tests_detail}
        gates["code_quality"] = {"status": ruff_status, "detail": ruff_detail}
    else:
        gates["tests"] = {"status": "BLOCKED", "detail": "run again with --run-static"}
        gates["code_quality"] = {"status": "BLOCKED", "detail": "run again with --run-static"}
    gates["package"] = (
        package_gate(generated_at)
        if args.run_package
        else {"status": "BLOCKED", "detail": "run again with --run-package"}
    )

    catalog_status, catalog_detail = command_status([sys.executable, str(ROOT / "tools" / "build_catalog.py"), "--check"])
    gates["catalog"] = {"status": catalog_status, "detail": catalog_detail}
    gates["public_tree"] = {"status": "PASS" if not public_errors else "FAIL", "errors": public_errors}
    gates["source_provenance"] = {
        "status": "PASS" if not provenance_errors else "FAIL",
        "errors": provenance_errors,
    }
    gates["privacy"] = {"status": "PASS" if not privacy_errors else "FAIL", "errors": privacy_errors}
    gates["secrets"] = {"status": "PASS" if not secret_errors else "FAIL", "errors": secret_errors}
    gates["community_files"] = structural_gate([
        "README.md", "README.zh-CN.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "SUPPORT.md",
        ".github/CODEOWNERS", ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/bug.yml",
    ])
    license_errors = audit_release_metadata(ROOT)
    gates["license"] = {
        "status": "PASS" if not license_errors else "FAIL",
        "spdx": "Apache-2.0",
        "errors": license_errors,
    }
    gates["citation"] = structural_gate(["CITATION.cff", "docs/release/CITATION_DECISION.md"])
    gates["ansys_terms_docs"] = structural_gate([
        "docs/ANSYS_USAGE_AND_COMPLIANCE.md", "docs/STUDENT_PRODUCT_LIMITS.md", "docs/release/OFFICIAL_SOURCE_AUDIT.md",
    ])
    gates["platform_docs"] = structural_gate([
        "docs/TESTED_ENVIRONMENTS.md", "docs/tutorials/install-windows.md", "docs/tutorials/install-macos.md",
    ])

    cli_errors: list[str] = []
    for command in (["list"], ["info", "mechanics", "static-cantilever"], ["doctor"], ["report"]):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                if cli_main(command):
                    cli_errors.append(" ".join(command))
        except Exception as exc:  # noqa: BLE001 - audit records any CLI traceback as a failure
            cli_errors.append(f"{' '.join(command)}: {type(exc).__name__}")
    gates["windows_core"] = {
        "status": "PASS" if platform.system() == "Windows" and not cli_errors else "BLOCKED" if platform.system() != "Windows" else "FAIL",
        "detail": "local Windows core smoke" if platform.system() == "Windows" else "not running on Windows",
        "errors": cli_errors,
    }
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    macos_configured = "macos-latest" in workflow and "python -m pip install -e \".[dev]\"" in workflow
    gates["macos_core"] = {
        "status": "PASS" if macos_configured else "FAIL",
        "detail": "static CI configured; macOS solver execution not locally validated",
    }

    known_limitations = (ROOT / "docs" / "known-limitations.md").read_text(encoding="utf-8")
    regression_qualifications: list[dict[str, object]] = []
    regression_errors: list[str] = []
    for name, (domain, case) in REPRESENTATIVE.items():
        record = latest_run(domain, case)
        observed_status = str(record.get("status")) if record else "MISSING"
        if record is None:
            regression_errors.append(f"{domain}/{case}: latest durable run record is missing")
        elif observed_status not in CASE_STATUSES:
            regression_errors.append(f"{domain}/{case}: invalid run status {observed_status!r}")
        result = record.get("result") if record else None
        result_status = str(result.get("status")) if isinstance(result, dict) else None
        if result_status is not None and result_status != observed_status:
            regression_errors.append(
                f"{domain}/{case}: run status {observed_status} disagrees with result status {result_status}"
            )
        regression_qualifications.append({
            "name": name,
            "domain": domain,
            "case": case,
            "observed_status": observed_status,
            "result_status": result_status,
            "record": record,
        })

    historical_path = ROOT / "docs" / "release" / "SOLVER_REGRESSION_RESULTS.json"
    try:
        historical_regressions = json.loads(historical_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        regression_errors.append(f"historical solver regression disclosure is unreadable: {exc}")
    else:
        historical_cases = historical_regressions.get("cases", {})
        for name in REPRESENTATIVE:
            historical_status = str(historical_cases.get(name, {}).get("status", "MISSING"))
            if historical_status not in CASE_STATUSES:
                regression_errors.append(f"historical {name}: invalid or missing status {historical_status!r}")
        regression_qualifications.append({
            "name": "historical_release_regressions",
            "observed_statuses": {
                name: historical_cases.get(name, {}).get("status", "MISSING") for name in REPRESENTATIVE
            },
            "evidence": "docs/release/SOLVER_REGRESSION_RESULTS.json",
        })
    for disclosure in ("`electromagnetics/electrostatic`", "historical `FAIL`", "separately `BLOCKED`"):
        if disclosure not in known_limitations:
            regression_errors.append(f"known limitations missing solver disclosure: {disclosure}")
    gates["solver_evidence_integrity"] = evidence_integrity_gate(
        regression_qualifications, regression_errors
    )

    physics_qualifications: list[dict[str, object]] = []
    physics_errors: list[str] = []
    for case in catalog_cases(ROOT):
        if case.status == "PASS":
            continue
        basis = case.reference or case.evidence
        evidence_exists = bool(basis and (ROOT / basis).is_file())
        disclosed = f"`{case.domain}/{case.slug}`" in known_limitations
        if case.status != "NOT_RUN" and not evidence_exists:
            physics_errors.append(f"{case.domain}/{case.slug}: {case.status} lacks durable public evidence")
        if not disclosed:
            physics_errors.append(f"{case.domain}/{case.slug}: {case.status} is absent from known limitations")
        physics_qualifications.append({
            "domain": case.domain,
            "case": case.slug,
            "observed_status": case.status,
            "evidence": basis,
            "evidence_exists": evidence_exists,
            "known_limitations_disclosed": disclosed,
        })

    case_j_record = latest_run("phase_reactive", "reactive-cht")
    case_j_status = str(case_j_record.get("status")) if case_j_record else "MISSING"
    if case_j_record is None:
        physics_errors.append("phase_reactive/reactive-cht: latest durable run record is missing")
    elif case_j_status not in CASE_STATUSES:
        physics_errors.append(f"phase_reactive/reactive-cht: invalid status {case_j_status!r}")
    case_j_result = case_j_record.get("result") if case_j_record else None
    case_j_result_status = str(case_j_result.get("status")) if isinstance(case_j_result, dict) else None
    if case_j_result_status != case_j_status:
        physics_errors.append(
            f"phase_reactive/reactive-cht: run status {case_j_status} disagrees with result status {case_j_result_status}"
        )
    case_j_metrics = case_j_result.get("metrics", {}) if isinstance(case_j_result, dict) else {}
    energy_window = case_j_metrics.get("energy_balance_window", {})
    threshold = energy_window.get("threshold") if isinstance(energy_window, dict) else None
    relative_error = energy_window.get("relative_error") if isinstance(energy_window, dict) else None
    declared_pass = energy_window.get("passes") if isinstance(energy_window, dict) else None
    expected_pass = (
        relative_error <= threshold
        if isinstance(relative_error, (int, float)) and isinstance(threshold, (int, float))
        else None
    )
    if threshold != 0.1:
        physics_errors.append(f"phase_reactive/reactive-cht: energy threshold changed from 0.1 to {threshold!r}")
    if expected_pass is None or declared_pass is not expected_pass:
        physics_errors.append("phase_reactive/reactive-cht: energy check is internally inconsistent")
    checks = case_j_result.get("checks", {}) if isinstance(case_j_result, dict) else {}
    if isinstance(checks, dict) and checks.get("global_total_enthalpy_balance_lt_10pct") is not declared_pass:
        physics_errors.append("phase_reactive/reactive-cht: named physics check disagrees with energy evidence")
    physics_qualifications.append({
        "domain": "phase_reactive",
        "case": "reactive-cht-current-run",
        "observed_status": case_j_status,
        "result_status": case_j_result_status,
        "threshold": threshold,
        "relative_error": relative_error,
        "passes": declared_pass,
        "record": case_j_record,
    })
    gates["physics_evidence_integrity"] = evidence_integrity_gate(
        physics_qualifications, physics_errors
    )
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    required_identity = (
        'name = "agentic-simulation-lab"',
        'agentic-sim = "agentic_simulation_lab.cli:entrypoint"',
        "Charlie-Wang-03/agentic-simulation-lab",
    )
    identity_errors = [item for item in required_identity if item not in metadata]
    if not (ROOT / "src" / "agentic_simulation_lab").is_dir():
        identity_errors.append("src/agentic_simulation_lab")
    gates["public_identity"] = {
        "status": "PASS" if not identity_errors else "FAIL",
        "expected": "Agentic Simulation Lab / agentic-simulation-lab / agentic_simulation_lab / agentic-sim",
        "errors": identity_errors,
    }

    git_status, git_detail = command_status(["git", "-c", f"safe.directory={ROOT.as_posix()}", "status", "--porcelain"])
    gates["git_cleanliness"] = {
        "status": "PASS" if git_status == "PASS" and not git_detail else "FAIL",
        "detail": "private mother working tree is clean" if not git_detail else git_detail,
    }

    overall = "READY FOR PUBLICATION" if all(gate["status"] == "PASS" for gate in gates.values()) else "NOT READY FOR PUBLICATION"
    payload = {
        "schema_version": 1,
        "generated_at_utc": generated_at.isoformat(),
        "project": "agentic-simulation-lab",
        "version": "0.1.0",
        "overall": overall,
        "gates": gates,
    }
    assert all(gate["status"] in GATE_STATUSES for gate in gates.values())
    target = ROOT / "artifacts" / "release" / "release_readiness.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if overall == "READY FOR PUBLICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
