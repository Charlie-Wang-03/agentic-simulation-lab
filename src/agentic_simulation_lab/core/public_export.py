"""Deterministic, fail-closed export of a public candidate from one Git revision."""

from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
import tarfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

from .audit import GENERATED_SUFFIXES, audit_export
from .validation import validate_project

POLICY_VERSION = 1
ALLOWED_PREFIXES = (
    ".github/",
    "agent/",
    "assets/",
    "benchmarks/",
    "docs/",
    "references/",
    "src/",
    "tests/",
    "tools/",
)
ALLOWED_ROOT_FILES = {
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "DISCLAIMER.md",
    "environment.yml",
    "FINALIZATION_REPORT.md",
    "MANIFEST.in",
    "LICENSE",
    "migration_receipt.json",
    "PROJECT_REFACTOR_REPORT.md",
    "pyproject.toml",
    "README.md",
    "README.zh-CN.md",
    "SECURITY.md",
    "SUPPORT.md",
    "THIRD_PARTY_NOTICES.md",
}
ALLOWED_SPECIAL_FILES = {"config/local.example.toml"}
EXCLUDED_PREFIXES = ("artifacts/", "config/")


class PublicExportError(RuntimeError):
    """Raised before extraction when the revision, policy, or destination is unsafe."""


def _run_git(root: Path, arguments: list[str], *, binary: bool = False) -> bytes | str:
    executable = shutil.which("git")
    if not executable:
        raise PublicExportError("Git executable was not found")
    try:
        completed = subprocess.run(
            [executable, "-c", f"safe.directory={root.as_posix()}", *arguments],
            cwd=root,
            capture_output=True,
            text=not binary,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PublicExportError(f"Git command failed safely: {type(exc).__name__}: {exc}") from exc
    if completed.returncode:
        stderr = completed.stderr.decode(errors="replace") if binary else completed.stderr
        raise PublicExportError(f"Git command exited {completed.returncode}: {stderr.strip()[-1000:]}")
    return completed.stdout


def resolve_revision(root: Path, revision: str) -> str:
    if not revision or revision.startswith("-"):
        raise PublicExportError("revision must be a non-option Git revision")
    value = _run_git(root, ["rev-parse", "--verify", f"{revision}^{{commit}}"])
    assert isinstance(value, str)
    commit = value.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit.casefold()):
        raise PublicExportError("Git did not resolve a full commit hash")
    return commit


def _selection(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise PublicExportError(f"unsafe archive path: {path!r}")
    if path in ALLOWED_SPECIAL_FILES or path in ALLOWED_ROOT_FILES or path.startswith(ALLOWED_PREFIXES):
        if pure.suffix.casefold() in GENERATED_SUFFIXES or path.endswith((".tmp", ".bak", "~")):
            raise PublicExportError(f"prohibited generated/proprietary file is tracked: {path}")
        return "include"
    if path.startswith(EXCLUDED_PREFIXES):
        return "exclude"
    raise PublicExportError(f"tracked path is not covered by public export policy: {path}")


def _tree_hash(files: list[dict[str, str]]) -> str:
    digest = hashlib.sha256()
    for item in files:
        digest.update(item["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(item["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def export_revision(
    root: Path,
    revision: str,
    destination: Path,
    *,
    auditor: Callable[[Path], list[str]] | None = None,
) -> dict[str, Any]:
    """Export and audit one exact revision; never copy the working tree."""
    root = root.resolve()
    destination = destination.resolve()
    safe_area = (root / "artifacts").resolve()
    if not destination.is_relative_to(safe_area):
        raise PublicExportError("destination must stay under the project artifacts directory")
    if destination.exists():
        if not destination.is_dir():
            raise PublicExportError("destination exists and is not a directory")
        if any(destination.iterdir()):
            raise PublicExportError("destination exists and is not empty")
    commit = resolve_revision(root, revision)
    archive = _run_git(root, ["archive", "--format=tar", commit], binary=True)
    assert isinstance(archive, bytes)

    selected: list[tuple[str, bytes]] = []
    excluded: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise PublicExportError(f"archive contains unsupported link or special entry: {member.name}")
            decision = _selection(member.name)
            if decision == "exclude":
                excluded.append(member.name)
                continue
            stream = bundle.extractfile(member)
            if stream is None:
                raise PublicExportError(f"unable to read archived file: {member.name}")
            selected.append((member.name, stream.read()))
    selected.sort(key=lambda item: item[0])
    if not selected:
        raise PublicExportError("public export policy selected no files")

    files: list[dict[str, str]] = []
    try:
        destination.mkdir(parents=True, exist_ok=True)
        for relative, content in selected:
            target = destination.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(content)
            files.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
    except OSError as exc:
        raise PublicExportError(f"unable to write exported tree safely: {type(exc).__name__}: {exc}") from exc

    audit_errors = (
        auditor(destination)
        if auditor is not None
        else validate_project(destination) + audit_export(destination)
    )
    return {
        "schema_version": 1,
        "status": "PASS" if not audit_errors else "FAIL",
        "source_revision": commit,
        "policy_version": POLICY_VERSION,
        "destination": destination.relative_to(root).as_posix(),
        "file_count": len(files),
        "files": files,
        "excluded_tracked_files": sorted(excluded),
        "tree_sha256": _tree_hash(files),
        "audit": {"status": "PASS" if not audit_errors else "FAIL", "errors": audit_errors},
        "publication": {
            "status": "BLOCKED" if not (destination / "LICENSE").is_file() else "NOT_ASSESSED",
            "reason": (
                "approved Apache-2.0 LICENSE is missing"
                if not (destination / "LICENSE").is_file()
                else "clean export passed; package, CI, public-history, and commit-identity gates remain external"
            ),
        },
    }
