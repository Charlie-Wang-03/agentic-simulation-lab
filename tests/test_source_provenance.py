from pathlib import Path

from agentic_simulation_lab.core.audit import audit_source_provenance


def _evidence(root: Path) -> None:
    (root / "docs" / "release").mkdir(parents=True)
    (root / "docs" / "release" / "SOURCE_PROVENANCE.md").write_text("reviewed\n", encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.md").write_text("reviewed\n", encoding="utf-8")


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
    assert audit_source_provenance(tmp_path) == [
        "THIRD_PARTY_NOTICES.md: required source-provenance evidence is missing",
        "docs/release/SOURCE_PROVENANCE.md: required source-provenance evidence is missing",
    ]
