from types import SimpleNamespace

import agentic_simulation_lab.core.audit as audit_module
from agentic_simulation_lab.core.audit import audit, audit_release_metadata
from agentic_simulation_lab.core.paths import project_root


def test_public_tree_has_no_private_paths():
    assert audit(project_root()) == []


def test_release_metadata_has_exact_approved_license():
    assert audit_release_metadata(project_root()) == []


def test_release_metadata_rejects_missing_license(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nlicense = "Apache-2.0"\nlicense-files = ["LICENSE"]\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "Apache License 2.0 does not license Ansys software.\n",
        encoding="utf-8",
    )

    assert audit_release_metadata(tmp_path) == [
        "LICENSE: approved Apache-2.0 repository license is missing"
    ]


def test_public_reference_rejects_private_network_endpoint(tmp_path):
    root = tmp_path / "artifacts" / "public-export"
    reference = root / "benchmarks" / "example" / "references" / "result.json"
    reference.parent.mkdir(parents=True)
    reference.write_text('{"error": "session failed on 127.0.0.1:5000"}\n', encoding="utf-8")

    errors = audit(root)

    assert errors == [
        "benchmarks/example/references/result.json: private or loopback network endpoint in public reference evidence"
    ]


def test_git_ignore_uses_repository_scoped_safe_directory(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / "public.txt").write_text("public\n", encoding="utf-8")
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(audit_module.subprocess, "run", fake_run)

    assert audit_module.audit(tmp_path) == []
    assert commands == [[
        "git",
        "-c",
        f"safe.directory={tmp_path.resolve().as_posix()}",
        "check-ignore",
        "--stdin",
    ]]
