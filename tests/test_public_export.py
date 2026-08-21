import subprocess
from pathlib import Path

import pytest

from agentic_simulation_lab.core.public_export import PublicExportError, export_revision


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def _repository(tmp_path: Path, files: dict[str, str]) -> tuple[Path, str]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.name", "Export Test")
    _git(root, "config", "user.email", "export-test@example.invalid")
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "fixture")
    return root, _git(root, "rev-parse", "HEAD")


def test_exact_revision_and_deterministic_hash(tmp_path):
    root, first = _repository(tmp_path, {"README.md": "version one\n", "artifacts/private.txt": "ignore\n"})
    (root / "README.md").write_text("version two\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "second")
    export_a = export_revision(root, first, root / "artifacts" / "export-a", auditor=lambda _: [])
    export_b = export_revision(root, first, root / "artifacts" / "export-b", auditor=lambda _: [])
    assert (root / "artifacts" / "export-a" / "README.md").read_text(encoding="utf-8") == "version one\n"
    assert not (root / "artifacts" / "export-a" / ".git").exists()
    assert not (root / "artifacts" / "export-a" / "artifacts").exists()
    assert export_a["files"] == export_b["files"]
    assert export_a["tree_sha256"] == export_b["tree_sha256"]


def test_local_config_is_excluded_but_example_is_exported(tmp_path):
    root, revision = _repository(
        tmp_path,
        {"README.md": "safe\n", "config/local.toml": "secret=true\n", "config/local.example.toml": "safe=false\n"},
    )
    result = export_revision(root, revision, root / "artifacts" / "export", auditor=lambda _: [])
    assert result["status"] == "PASS"
    assert not (root / "artifacts" / "export" / "config" / "local.toml").exists()
    assert (root / "artifacts" / "export" / "config" / "local.example.toml").is_file()


def test_prohibited_extension_is_rejected(tmp_path):
    root, revision = _repository(tmp_path, {"README.md": "safe\n", "benchmarks/model.cas": "binary-ish\n"})
    with pytest.raises(PublicExportError, match="prohibited"):
        export_revision(root, revision, root / "artifacts" / "export", auditor=lambda _: [])


def test_unknown_private_path_is_rejected(tmp_path):
    root, revision = _repository(tmp_path, {"README.md": "safe\n", "private/notes.txt": "do not export\n"})
    with pytest.raises(PublicExportError, match="not covered"):
        export_revision(root, revision, root / "artifacts" / "export", auditor=lambda _: [])


def test_nonempty_destination_fails_without_overwrite(tmp_path):
    root, revision = _repository(tmp_path, {"README.md": "safe\n"})
    destination = root / "artifacts" / "export"
    destination.mkdir(parents=True)
    sentinel = destination / "keep.txt"
    sentinel.write_text("keep\n", encoding="utf-8")
    with pytest.raises(PublicExportError, match="not empty"):
        export_revision(root, revision, destination, auditor=lambda _: [])
    assert sentinel.read_text(encoding="utf-8") == "keep\n"


def test_exported_tree_auditor_controls_status(tmp_path):
    root, revision = _repository(tmp_path, {"README.md": "safe\n"})
    observed = []

    def reject_export(target):
        observed.append(target)
        assert (target / "README.md").is_file()
        return ["synthetic exported-tree audit failure"]

    destination = root / "artifacts" / "export"
    result = export_revision(root, revision, destination, auditor=reject_export)
    assert observed == [destination.resolve()]
    assert result["status"] == "FAIL"
    assert result["audit"]["errors"] == ["synthetic exported-tree audit failure"]


def test_destination_outside_project_artifacts_is_rejected(tmp_path):
    root, revision = _repository(tmp_path, {"README.md": "safe\n"})
    with pytest.raises(PublicExportError, match="artifacts"):
        export_revision(root, revision, tmp_path / "external", auditor=lambda _: [])
