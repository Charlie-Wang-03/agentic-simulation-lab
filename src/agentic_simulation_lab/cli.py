from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .core.environment import inspect_environment
from .core.execution import execute
from .core.paths import artifacts_root, project_root
from .core.registry import cases, find_case, manifests
from .core.reporting import metrics
from .core.status import VALID_STATUSES
from .core.validation import validate_project


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _json_option(command: argparse.ArgumentParser) -> None:
    command.add_argument("--json", action="store_true", help="emit stable machine-readable JSON")


def parser() -> argparse.ArgumentParser:
    app = argparse.ArgumentParser(
        prog="agentic-sim",
        description="Explore educational, physics-validated Ansys automation cases",
    )
    commands = app.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="inspect optional solver integrations without launching them")
    doctor.add_argument("--probe", nargs="?", const="all", help="inspect executable availability for a target; does not launch it")
    _json_option(doctor)
    listing = commands.add_parser("list", help="list catalog cases")
    listing.add_argument("--domain")
    listing.add_argument("--status", choices=sorted(VALID_STATUSES))
    listing.add_argument("--solver", help="case-insensitive solver label substring")
    listing.add_argument("--role", choices=["benchmark", "dataset", "utility"])
    _json_option(listing)
    info = commands.add_parser("info", help="show a domain or case")
    info.add_argument("domain")
    info.add_argument("case", nargs="?")
    _json_option(info)
    run = commands.add_parser("run", help="run one case or a domain suite")
    run.add_argument("domain")
    choice = run.add_mutually_exclusive_group(required=True)
    choice.add_argument("--case")
    choice.add_argument("--suite", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--timeout", type=_positive_int, metavar="SECONDS", help="override the case timeout")
    _json_option(run)
    validate = commands.add_parser("validate", help="validate manifests and paths")
    validate.add_argument("domain", nargs="?")
    validate.add_argument("--case")
    _json_option(validate)
    audit = commands.add_parser("audit", help="run the public-tree audit")
    _json_option(audit)
    report = commands.add_parser("report", help="print catalog-derived metrics")
    _json_option(report)
    paths = commands.add_parser("paths", help="show resolved project paths")
    _json_option(paths)
    dataset = commands.add_parser("dataset", help="inspect or validate a Dataset Contract v1 payload")
    dataset_commands = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_info = dataset_commands.add_parser("info", help="inspect dataset metadata without loading NumPy arrays")
    dataset_info.add_argument("path")
    _json_option(dataset_info)
    dataset_validate = dataset_commands.add_parser("validate", help="validate dataset metadata and numerical payloads")
    dataset_validate.add_argument("path")
    _json_option(dataset_validate)
    return app


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2))


def _human_list(selected: list[object]) -> None:
    if not selected:
        print("No catalog cases match the selected filters.")
        return
    headers = ("DOMAIN", "CASE", "ROLE", "SOLVER", "STATUS")
    rows = [(case.domain, case.slug, case.role, case.solver, case.status) for case in selected]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(row))))
    print(f"\n{len(rows)} case(s)")


def _domain_manifest(domain: str, root: object) -> dict[str, object] | None:
    for _, data in manifests(root):
        if data["domain"] == domain:
            return data
    return None


def _case_payload(case: object, manifest: dict[str, object]) -> dict[str, object]:
    payload = asdict(case)
    payload["validation_basis"] = case.reference or case.evidence or "not declared"
    payload["requirements"] = manifest.get("required_products", [])
    payload["commands"] = {
        "dry_run": f"agentic-sim run {case.domain} --case {case.slug} --dry-run",
        "run": f"agentic-sim run {case.domain} --case {case.slug}",
    }
    return payload


def _human_info(payload: dict[str, object]) -> None:
    print(f"{payload['domain']}/{payload['slug']} — {payload['title']}")
    print(f"Status: {payload['status']} (historical catalog evidence)")
    print(f"Role: {payload['role']} | Solver: {payload['solver']} | Analysis: {payload['analysis']}")
    print(f"Validation basis: {payload['validation_basis']}")
    print(f"Requirements: {', '.join(payload['requirements']) or 'none declared'}")
    print(f"Timeout: {payload['timeout_seconds']} seconds")
    print(f"Authoritative result: {payload['result_file']} ({payload['result_format']})")
    print(f"Dry-run: {payload['commands']['dry_run']}")
    print(f"Run: {payload['commands']['run']}")


def _human_doctor(payload: dict[str, object]) -> None:
    print(f"Python {payload['python']['version']} | {payload['platform']}")
    print("Solver clients (diagnosis only; no solver launched):")
    for name, item in payload["packages"].items():
        version = f" {item['version']}" if item["version"] else ""
        executable = payload["executables"][name]["status"]
        print(f"  {name:16} package={item['status']}{version} executable={executable}")
    if "probe" in payload:
        print(f"Probe: {payload['probe']['target']} — STATIC_ONLY")


def _human_report(payload: dict[str, object]) -> None:
    print(f"Catalog: {payload['domains']} domains, {payload['cases']} cases")
    print("Statuses: " + ", ".join(f"{key}={value}" for key, value in payload["statuses"].items()))
    print("Roles: " + ", ".join(f"{key}={value}" for key, value in payload["roles"].items()))
    print("Use --json for the complete solver coverage map.")


def _human_validation(payload: dict[str, object]) -> None:
    print(f"Validation: {payload['status']}")
    for error in payload["errors"]:
        print(f"  - {error}")
    if payload.get("selection"):
        case = payload["selection"]
        print(f"Selected: {case['domain']}/{case['slug']} ({case['status']} catalog status)")
    if payload.get("latest_run"):
        print(f"Latest run: {payload['latest_run']['status']}")


def _dataset_info_payload(dataset: object) -> dict[str, object]:
    metadata = dataset.metadata
    return {
        "descriptor": str(dataset.descriptor_path),
        "schema_version": metadata["schema_version"],
        "dataset_id": metadata["dataset_id"],
        "name": metadata["name"],
        "source": metadata["source"],
        "representation": metadata["representation"],
        "parameters": metadata["parameters"],
        "fields": metadata["fields"],
        "geometry": metadata["geometry"],
        "sample_count": len(dataset),
        "provenance": metadata["provenance"],
        "validation": metadata["validation"],
        "splits": metadata["splits"],
    }


def _human_dataset_info(payload: dict[str, object]) -> None:
    print(f"{payload['dataset_id']} — {payload['name']}")
    print(f"Dataset Contract v{payload['schema_version']} | {payload['sample_count']} sample(s)")
    representation = payload["representation"]
    print(
        "Representation: "
        f"{representation.get('kind', 'unspecified')}, {representation.get('mesh', 'unspecified')}, "
        f"{representation.get('temporal', 'unspecified')}"
    )
    print("Parameters: " + ", ".join(item["name"] for item in payload["parameters"]))
    print("Fields: " + ", ".join(item["name"] for item in payload["fields"]))
    print(f"Descriptor: {payload['descriptor']}")


def _human_dataset_validation(payload: dict[str, object]) -> None:
    print(f"Dataset structure and payload: {payload['status']}")
    print(f"Samples: {payload.get('sample_count', 0)}")
    physics = payload.get("physics_validation")
    if isinstance(physics, dict):
        print(
            "Physics validation evidence: "
            f"{physics.get('status', 'NOT_DECLARED')} ({physics.get('basis', 'basis not declared')})"
        )
    for error in payload.get("errors", []):
        print(f"  - {error}")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = project_root()
    if args.command == "doctor":
        payload = inspect_environment(args.probe)
        _print_json(payload) if args.json else _human_doctor(payload)
        return 0
    if args.command == "list":
        if args.domain and _domain_manifest(args.domain, root) is None:
            print(f"unknown domain: {args.domain}", file=sys.stderr)
            return 2
        selected = cases(root, args.domain)
        if args.status:
            selected = [case for case in selected if case.status == args.status]
        if args.solver:
            needle = args.solver.casefold()
            selected = [case for case in selected if needle in case.solver.casefold()]
        if args.role:
            selected = [case for case in selected if case.role == args.role]
        payload = {"cases": [asdict(case) for case in selected], "count": len(selected)}
        _print_json(payload) if args.json else _human_list(selected)
        return 0
    if args.command == "info":
        manifest = _domain_manifest(args.domain, root)
        if manifest is None:
            print(f"unknown domain: {args.domain}", file=sys.stderr)
            return 2
        if args.case:
            try:
                payload = _case_payload(find_case(args.domain, args.case, root), manifest)
            except KeyError as exc:
                print(exc.args[0], file=sys.stderr)
                return 2
            _print_json(payload) if args.json else _human_info(payload)
            return 0
        if args.json:
            _print_json(manifest)
        else:
            requirements = ", ".join(manifest.get("required_products", [])) or "none declared"
            print(f"{manifest['title']} ({manifest['domain']}): {len(manifest['cases'])} cases; requirements: {requirements}")
        return 0
    if args.command == "run":
        try:
            selected = cases(root, args.domain) if args.suite else [find_case(args.domain, args.case, root)]
        except KeyError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2
        runnable = [case for case in selected if case.role != "utility"]
        if not runnable:
            print("no executable benchmark or dataset cases selected", file=sys.stderr)
            return 2
        records = [execute(case, args.dry_run, args.timeout) for case in runnable]
        if args.json:
            _print_json({"runs": records})
        else:
            for record in records:
                suffix = " (dry-run)" if record["dry_run"] else ""
                print(f"{record['domain']}/{record['case']}: {record['status']}{suffix}")
                print(f"  result: {record['authoritative_result']} | timeout: {record['timeout_seconds']}s")
        return 0 if all(r["status"] in {"PASS", "NOT_RUN"} for r in records) else 1
    if args.command == "validate":
        errors = validate_project(root)
        selection = None
        latest_run = None
        if args.case and not args.domain:
            errors.append("--case requires a domain")
        elif args.domain:
            try:
                if args.case:
                    selected_case = find_case(args.domain, args.case, root)
                    selection = asdict(selected_case)
                    run_records = sorted(
                        (artifacts_root(root) / "runs" / args.domain / args.case).glob("*/run.json")
                    )
                    if run_records:
                        latest_run = json.loads(run_records[-1].read_text(encoding="utf-8"))
                elif not cases(root, args.domain):
                    errors.append(f"unknown domain: {args.domain}")
            except KeyError as exc:
                errors.append(exc.args[0])
        payload = {
            "status": "PASS" if not errors else "FAIL", "errors": errors,
            "selection": selection, "latest_run": latest_run,
        }
        _print_json(payload) if args.json else _human_validation(payload)
        return bool(errors)
    if args.command == "audit":
        from .core.audit import audit, audit_release_metadata, audit_source_provenance
        errors = validate_project(root) + audit(root) + audit_source_provenance(root) + audit_release_metadata(root)
        payload = {"status": "PASS" if not errors else "FAIL", "errors": errors}
        _print_json(payload) if args.json else _human_validation(payload)
        return bool(errors)
    if args.command == "report":
        payload = metrics()
        _print_json(payload) if args.json else _human_report(payload)
        return 0
    if args.command == "paths":
        diagnosed = inspect_environment()
        payload = {
            "root": str(root), "artifacts": str(artifacts_root(root)),
            "benchmarks": str(root / "benchmarks"), "local_config": str(root / "config" / "local.toml"),
            "solver_roots": diagnosed["student_roots"],
        }
        _print_json(payload) if args.json else print("\n".join(f"{key}: {value}" for key, value in payload.items()))
        return 0
    if args.command == "dataset":
        from .datasets import DatasetContractError, open_dataset, validate_dataset

        if args.dataset_command == "info":
            try:
                payload = _dataset_info_payload(open_dataset(args.path))
            except DatasetContractError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            _print_json(payload) if args.json else _human_dataset_info(payload)
            return 0
        payload = validate_dataset(args.path)
        _print_json(payload) if args.json else _human_dataset_validation(payload)
        return 0 if payload["status"] == "PASS" else 1
    return 2


def entrypoint() -> int:
    return main()
