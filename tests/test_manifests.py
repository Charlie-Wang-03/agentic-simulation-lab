from agentic_simulation_lab.core.execution import execute
from agentic_simulation_lab.core.paths import project_root
from agentic_simulation_lab.core.registry import find_case, manifests


def test_all_domain_manifests_load():
    loaded = list(manifests(project_root()))
    assert len(loaded) == 11


def test_case_slugs_are_unique_per_domain():
    for _, manifest in manifests(project_root()):
        slugs = [case["slug"] for case in manifest["cases"]]
        assert len(slugs) == len(set(slugs))


def test_schema_v2_declares_authoritative_results_for_executable_cases():
    for _, manifest in manifests(project_root()):
        assert manifest["schema_version"] == 2
        for case in manifest["cases"]:
            if case.get("role", "benchmark") != "utility":
                assert case["result_file"]
                assert case["result_format"] in {"v1", "legacy"}


def test_flagship_dataset_uses_native_case_result_contract():
    case = find_case("cfd", "fluent-parametric-dataset", project_root())
    assert case.result_file == "case-result.json"
    assert case.result_format == "v1"
    record = execute(case, dry_run=True)
    assert record["status"] == "NOT_RUN"
    assert record["authoritative_result"].endswith("/case-result.json")
