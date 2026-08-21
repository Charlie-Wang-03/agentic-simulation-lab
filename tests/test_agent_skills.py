from agentic_simulation_lab.core.paths import project_root


def test_retained_skills_have_reliability_contract_sections():
    skill_root = project_root() / "agent" / "skills"
    skills = sorted(skill_root.glob("*/SKILL.md"))
    assert [path.parent.name for path in skills] == [
        "catalog-navigation",
        "diagnose-solver",
        "new-benchmark",
        "project-audit",
        "result-validation",
        "run-and-validate",
    ]
    for path in skills:
        text = path.read_text(encoding="utf-8")
        for heading in (
            "## When to use",
            "## Preconditions",
            "## Main commands",
            "## Evidence source",
            "## Stop conditions",
            "## Forbidden shortcuts",
            "## Expected output",
        ):
            assert heading in text, f"{path.relative_to(project_root())} missing {heading}"


def test_workflow_names_current_contract_authorities():
    text = (project_root() / "agent" / "WORKFLOW.md").read_text(encoding="utf-8")
    for term in (
        "manifest schema v2",
        "Canonical Case Result Contract v1",
        "Dataset Contract v1",
        "Dataset validation PASS does not imply",
        "PASS",
        "FAIL",
        "BLOCKED",
        "PARTIAL",
        "NOT_RUN",
    ):
        assert term in text


def test_no_repository_links_to_removed_duplicate_skills():
    removed = {"benchmark-execution", "physics-validation", "environment-diagnosis", "release-audit"}
    for path in project_root().rglob("*.md"):
        if any(part in {".git", "artifacts", ".venv"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(f"agent/skills/{name}" in text for name in removed)
