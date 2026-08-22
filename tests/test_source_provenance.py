import json
from pathlib import Path

from agentic_simulation_lab.core.audit import (
    audit_publication_decisions,
    audit_source_provenance,
    publication_corpus_fingerprint,
)


def _evidence(root: Path) -> None:
    (root / "docs" / "release").mkdir(parents=True)
    (root / "docs" / "release" / "SOURCE_PROVENANCE.md").write_text("reviewed\n", encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.md").write_text("reviewed\n", encoding="utf-8")
    _inventory(root, {})


def _inventory(root: Path, units: dict) -> None:
    path = root / "docs" / "release" / "SOLVER_DERIVED_PUBLICATION_INVENTORY.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "review_units": units}), encoding="utf-8")
    decisions = {
        unit_id: {
            "decision": (
                "APPROVED" if unit.get("status") == "CLEARED" else "NOT_APPROVED"
            ),
            "rationale": "test-rationale",
        }
        for unit_id, unit in units.items()
    }
    decision_path = root / "docs" / "release" / "MAINTAINER_PUBLICATION_DECISIONS.json"
    decision_path.write_text(
        json.dumps({
            "schema_version": 1,
            "future_research_boundary": "Future research requires a new decision.",
            "rationales": {"test-rationale": {"summary": "test"}},
            "decisions": decisions,
        }),
        encoding="utf-8",
    )


def _review_unit(root: Path, status: str, **overrides) -> dict:
    unit = {
        "domain": "mechanics",
        "source_paths": ["benchmarks/mechanics/references/*.json"],
        "generation_date": "unknown",
        "solver_product": "Mechanical",
        "license_type": "unknown",
        "applicable_agreement": "unknown",
        "run_purpose": "unknown",
        "source_input_provenance": "unknown",
        "proprietary_vendor_assets_involved": "unknown",
        "publication_basis": "unknown",
        "status": status,
    }
    unit.update(overrides)
    unit["source_fingerprint"] = publication_corpus_fingerprint(root, unit["source_paths"])
    return unit


def _cleared_unit(root: Path, **overrides) -> dict:
    return _review_unit(
        root,
        "CLEARED",
        generation_date="2026-08-22",
        solver_product="Mechanical",
        license_type="Research",
        applicable_agreement="maintainer-reviewed record",
        run_purpose="physics validation",
        source_input_provenance="repository-authored model",
        proprietary_vendor_assets_involved="no",
        publication_basis="maintainer-reviewed publication basis",
        **overrides,
    )


def _reference(root: Path, name: str = "historical_results.json", content: str = '{"status": "PASS"}\n') -> Path:
    path = root / "benchmarks" / "mechanics" / "references" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_provenance_rejects_unclassified_geometry(tmp_path):
    _evidence(tmp_path)
    asset = tmp_path / "assets" / "rocky" / "unknown.stl"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"solid unknown\nendsolid unknown\n")

    assert audit_source_provenance(tmp_path) == ["assets/rocky/unknown.stl: unclassified geometry asset"]


def test_provenance_rejects_external_media(tmp_path):
    _evidence(tmp_path)
    image = tmp_path / "docs" / "vendor-logo.png"
    image.parent.mkdir(exist_ok=True)
    image.write_bytes(b"not really a png")

    assert audit_source_provenance(tmp_path) == [
        "docs/vendor-logo.png: external media/logo provenance is not allowlisted"
    ]


def test_provenance_requires_reviewed_evidence(tmp_path):
    errors = audit_source_provenance(tmp_path)
    assert errors[:4] == [
        "THIRD_PARTY_NOTICES.md: required source-provenance evidence is missing",
        "docs/release/SOURCE_PROVENANCE.md: required source-provenance evidence is missing",
        "docs/release/SOLVER_DERIVED_PUBLICATION_INVENTORY.json: required source-provenance evidence is missing",
        "docs/release/MAINTAINER_PUBLICATION_DECISIONS.json: required source-provenance evidence is missing",
    ]
    assert any("unable to load legal/evidence statuses" in error for error in errors)
    assert any("unable to load maintainer decisions" in error for error in errors)


def test_provenance_accepts_maintainer_approved_residual_risk_without_clearing(tmp_path):
    _evidence(tmp_path)
    _reference(tmp_path)
    _inventory(tmp_path, {
        "mechanics-solver-run-corpus": _review_unit(tmp_path, "LEGAL_REVIEW_REQUIRED")
    })
    decision_path = tmp_path / "docs" / "release" / "MAINTAINER_PUBLICATION_DECISIONS.json"
    decision_record = json.loads(decision_path.read_text(encoding="utf-8"))
    decision_record["decisions"]["mechanics-solver-run-corpus"]["decision"] = (
        "APPROVED_WITH_RESIDUAL_RISK"
    )
    decision_path.write_text(json.dumps(decision_record), encoding="utf-8")
    evidence = tmp_path / "docs" / "assets" / "simulations" / "mechanics" / "case.evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(
        json.dumps({
            "publication_review": {
                "review_unit": "mechanics-solver-run-corpus",
                "generation_date": "unknown",
                "license_type": "unknown",
                "applicable_agreement": "unknown",
                "run_purpose": "unknown",
                "source_input_provenance": "unknown",
                "proprietary_vendor_assets_involved": "unknown",
                "publication_basis": "unknown",
                "status": "LEGAL_REVIEW_REQUIRED",
            }
        }),
        encoding="utf-8",
    )

    assert audit_source_provenance(tmp_path) == []
    gate = audit_publication_decisions(tmp_path)
    assert gate["outcome"] == "PASS WITH ACCEPTED RESIDUAL LEGAL RISK"
    assert gate["warnings"]


def test_provenance_rejects_cleared_review_with_unknown_basis(tmp_path):
    _evidence(tmp_path)
    _inventory(tmp_path, {
        "cfd-solver-run-corpus": _review_unit(
            tmp_path,
            "CLEARED",
            domain="cfd",
            source_paths=["benchmarks/cfd/references/*.json"],
            generation_date="2026-08-22",
            solver_product="Fluent",
            license_type="Research",
            applicable_agreement="maintainer-reviewed record",
            run_purpose="physics validation",
            source_input_provenance="repository-authored model",
            proprietary_vendor_assets_involved="no",
            publication_basis="maintainer-reviewed publication basis",
        )
    })
    evidence = tmp_path / "docs" / "assets" / "simulations" / "cfd" / "case.evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(
        json.dumps({
            "publication_review": {
                "review_unit": "cfd-solver-run-corpus",
                "generation_date": "2026-08-22",
                "license_type": "Research",
                "applicable_agreement": "maintainer-reviewed record",
                "run_purpose": "physics validation",
                "source_input_provenance": "repository-authored model",
                "proprietary_vendor_assets_involved": "no",
                "publication_basis": "unknown",
                "status": "CLEARED",
            }
        }),
        encoding="utf-8",
    )

    assert audit_source_provenance(tmp_path) == [
        "docs/assets/simulations/cfd/case.evidence.json: CLEARED publication review has unresolved fields: publication_basis"
    ]


def test_provenance_rejects_unregistered_solver_reference(tmp_path):
    _evidence(tmp_path)
    reference = tmp_path / "benchmarks" / "thermal" / "references" / "historical_results.json"
    reference.parent.mkdir(parents=True)
    reference.write_text('{"status": "PASS", "temperature_k": 373.15}\n', encoding="utf-8")

    assert audit_source_provenance(tmp_path) == [
        "benchmarks/thermal/references/historical_results.json: solver-derived reference is not assigned to a publication review unit"
    ]


def test_cleared_corpus_accepts_exact_reviewed_source_set(tmp_path):
    _evidence(tmp_path)
    _reference(tmp_path)
    _inventory(tmp_path, {"mechanics-solver-run-corpus": _cleared_unit(tmp_path)})

    assert audit_source_provenance(tmp_path) == []


def test_cleared_corpus_rejects_new_matching_reference(tmp_path):
    _evidence(tmp_path)
    _reference(tmp_path)
    _inventory(tmp_path, {"mechanics-solver-run-corpus": _cleared_unit(tmp_path)})
    _reference(tmp_path, "new_solver_result.json", '{"displacement_mm": 0.1}\n')

    assert audit_source_provenance(tmp_path) == [
        "docs/release/SOLVER_DERIVED_PUBLICATION_INVENTORY.json: review unit mechanics-solver-run-corpus source corpus changed; fingerprint is stale and re-review is required"
    ]


def test_cleared_corpus_rejects_modified_reviewed_reference(tmp_path):
    _evidence(tmp_path)
    reference = _reference(tmp_path)
    _inventory(tmp_path, {"mechanics-solver-run-corpus": _cleared_unit(tmp_path)})
    reference.write_text('{"status": "PASS", "displacement_mm": 0.2}\n', encoding="utf-8")

    assert audit_source_provenance(tmp_path) == [
        "docs/release/SOLVER_DERIVED_PUBLICATION_INVENTORY.json: review unit mechanics-solver-run-corpus source corpus changed; fingerprint is stale and re-review is required"
    ]


def test_cleared_corpus_rejects_deleted_reviewed_reference(tmp_path):
    _evidence(tmp_path)
    reference = _reference(tmp_path)
    _inventory(tmp_path, {"mechanics-solver-run-corpus": _cleared_unit(tmp_path)})
    reference.unlink()

    assert audit_source_provenance(tmp_path) == [
        "docs/release/SOLVER_DERIVED_PUBLICATION_INVENTORY.json: review unit mechanics-solver-run-corpus source corpus changed; fingerprint is stale and re-review is required"
    ]


def test_publication_fingerprint_is_portable_across_json_line_endings(tmp_path):
    reference = _reference(tmp_path)
    reference.write_bytes(b'{\r\n  "status": "PASS"\r\n}\r\n')
    source_paths = ["benchmarks/mechanics/references/*.json"]
    windows_fingerprint = publication_corpus_fingerprint(tmp_path, source_paths)
    reference.write_bytes(b'{\n  "status": "PASS"\n}\n')

    assert publication_corpus_fingerprint(tmp_path, source_paths) == windows_fingerprint
