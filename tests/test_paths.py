from agentic_simulation_lab.core.paths import artifacts_root, project_root


def test_paths_are_project_relative():
    root = project_root()
    assert (root / "pyproject.toml").is_file()
    assert artifacts_root(root) == root / "artifacts"
