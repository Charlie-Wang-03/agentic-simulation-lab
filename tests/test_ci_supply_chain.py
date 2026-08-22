from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def test_key_github_actions_are_pinned_to_verified_commits():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert (
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0"
        in workflow
    )
    assert (
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0"
        in workflow
    )
