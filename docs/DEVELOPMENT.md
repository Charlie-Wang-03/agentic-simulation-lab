# Development

Create the project environment with `python tools/bootstrap.py --extras dev`. Keep Ansys imports inside adapter functions or case execution paths. Add a manifest entry with a unique slug, explicit status, prerequisites, units, acceptance checks, and project-relative evidence before exposing a case through the CLI.

Run the maintained static pipeline:

```bash
python -m compileall -q src benchmarks tools tests
pytest
ruff check src tests tools benchmarks/phase_reactive/cases/smoke_reactive_cht.py benchmarks/electromagnetics/common/aedt_smoke_common.py benchmarks/electromagnetics/cases/smoke_aedt_connect.py benchmarks/electromagnetics/cases/smoke_hfss_connect.py
python tools/build_catalog.py --check
python tools/build_project_metrics.py --check
python tools/build_reference_summaries.py --check
python tools/validate_history.py --npz
python tools/check_public_tree.py
python tools/check_source_provenance.py
python tools/check_links.py
python tools/check_tutorial_pairs.py
python tools/check_subprocess_policy.py
python tools/check_dataset_portability.py
python tools/static_selftest.py
```

The full migrated benchmark corpus is compiled and manifest/reference-validated. Ruff is applied to the maintained package, tests, tools, and current release-blocking Case J; mechanically reformatting all historical solver scripts is outside the release freeze. The provenance gate rejects unclassified binary/media content and hash drift in reviewed geometry fixtures.
