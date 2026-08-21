import json

from agentic_simulation_lab.core.paths import project_root
from agentic_simulation_lab.core.registry import manifests


def test_reference_files_are_small_parseable_json():
    root = project_root()
    for _, manifest in manifests(root):
        for case in manifest["cases"]:
            evidence = case.get("evidence")
            if not evidence:
                continue
            path = root / evidence
            assert path.stat().st_size < 1_000_000
            json.loads(path.read_text(encoding="utf-8"))
