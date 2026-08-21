from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from agentic_simulation_lab.cli import main
from agentic_simulation_lab.datasets import DatasetContractError, open_dataset, sha256_file, validate_dataset


def _write_dataset(root: Path, *, defect: str | None = None) -> Path:
    root.mkdir()
    coordinates = np.asarray([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float64)
    connectivity = np.asarray([[0, 1, 2, 3]], dtype=np.int64)
    samples = []
    for index, reynolds_number in enumerate((100, 200)):
        sample_coordinates = coordinates.copy()
        sample_connectivity = connectivity.copy()
        velocity_x = np.full(4, float(index), dtype=np.float64)
        velocity_y = np.zeros(4, dtype=np.float64)
        pressure = np.linspace(0.0, 1.0, 4, dtype=np.float64)
        arrays = {
            "coordinates": sample_coordinates,
            "connectivity": sample_connectivity,
            "velocity_x": velocity_x,
            "velocity_y": velocity_y,
            "pressure": pressure,
        }
        if index == 1:
            if defect == "missing_array":
                arrays.pop("pressure")
            elif defect == "nonfinite":
                arrays["velocity_x"][0] = np.nan
            elif defect == "field_shape":
                arrays["pressure"] = np.ones(3, dtype=np.float64)
            elif defect == "connectivity":
                arrays["connectivity"][0, -1] = 99
            elif defect == "shared_geometry":
                arrays["coordinates"][0, 0] = 0.25
        path = root / f"sample_{index:03d}.npz"
        np.savez_compressed(path, **arrays)
        samples.append(
            {
                "id": f"sample_{index:03d}",
                "parameters": {
                    "reynolds_number": reynolds_number,
                    "lid_velocity": 1.0,
                    "cavity_length": 1.0,
                },
                "files": [{"path": path.name, "format": "npz", "sha256": sha256_file(path)}],
            }
        )
    index_path = root / "dataset_index.csv"
    index_path.write_text("sample_id,reynolds_number\nsample_000,100\nsample_001,200\n", encoding="utf-8")
    descriptor = {
        "schema_version": 1,
        "dataset_id": "test/tiny-cavity",
        "name": "Tiny cavity fixture",
        "source": {"case": "cfd/fluent-parametric-dataset", "physics_domain": "cfd"},
        "representation": {
            "kind": "eulerian_field",
            "mesh": "structured_quadrilateral",
            "temporal": "steady",
        },
        "parameters": [
            {
                "name": "reynolds_number",
                "units": "1",
                "meaning": "Ratio of inertial to viscous forces",
                "values": [100, 200],
                "provenance": "deterministic smoke sweep",
            },
            {
                "name": "lid_velocity",
                "units": "m/s",
                "meaning": "Moving-wall velocity",
                "values": [1.0],
                "provenance": "generation configuration",
            },
            {
                "name": "cavity_length",
                "units": "m",
                "meaning": "Square cavity side length",
                "values": [1.0],
                "provenance": "generation configuration",
            },
        ],
        "fields": [
            {"name": "velocity_x", "units": "m/s", "location": "node", "dtype": "float64", "shape": ["node"]},
            {"name": "velocity_y", "units": "m/s", "location": "node", "dtype": "float64", "shape": ["node"]},
            {"name": "pressure", "units": "Pa", "location": "node", "dtype": "float64", "shape": ["node"]},
        ],
        "geometry": {
            "shared": True,
            "dimensionality": 2,
            "coordinates": {"array": "coordinates", "units": "m", "dtype": "float64", "shape": ["node", 2]},
            "connectivity": {
                "array": "connectivity",
                "location": "cell",
                "index_base": 0,
                "dtype": "int64",
                "shape": ["cell", 4],
            },
        },
        "samples": samples,
        "provenance": {
            "generator": "synthetic pytest fixture",
            "source_case": "cfd/fluent-parametric-dataset",
            "solver": {"name": "none", "observed_version": "not applicable"},
            "packages": {},
            "generation_configuration": {"profile": "tiny"},
        },
        "validation": {
            "status": "PASS",
            "schema_reload": "PASS",
            "numerical_finiteness": "PASS",
            "shape_topology_consistency": "PASS",
            "physics": {
                "status": "PASS",
                "basis": "declared synthetic test evidence; not inferred from file validity",
                "source_case": "test/tiny-cavity",
            },
        },
        "splits": {
            "official": False,
            "assignments": {},
            "semantics": "No official train/validation/test split; pipeline demonstration only.",
        },
        "supporting_files": [
            {"path": index_path.name, "role": "human-readable index", "sha256": sha256_file(index_path)}
        ],
    }
    descriptor_path = root / "dataset.json"
    descriptor_path.write_text(json.dumps(descriptor, indent=2), encoding="utf-8")
    return descriptor_path


def _edit_descriptor(path: Path, edit) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    edit(payload)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_open_load_and_validate_end_to_end(tmp_path):
    descriptor = _write_dataset(tmp_path / "dataset")
    dataset = open_dataset(descriptor.parent)
    assert dataset.metadata["dataset_id"] == "test/tiny-cavity"
    assert len(dataset) == 2
    sample = dataset.load_sample(0)
    assert sample["parameters"]["reynolds_number"] == 100
    assert sample["velocity_x"].shape == (4,)
    report = validate_dataset(descriptor)
    assert report["status"] == "PASS"
    assert report["physics_validation"]["status"] == "PASS"
    assert dataset.validate()["status"] == "PASS"


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda payload: payload.pop("fields"), "descriptor missing fields"),
        (lambda payload: payload.update(schema_version=99), "unsupported dataset schema_version"),
        (lambda payload: payload["samples"][0]["files"][0].update(path="C:/private/sample.npz"), "unsafe"),
        (lambda payload: payload["samples"][0]["files"][0].update(path="../sample.npz"), "unsafe"),
        (lambda payload: payload.update(samples=["not-an-object"]), "each sample must be an object"),
        (lambda payload: payload.update(parameters={"not": "a list"}), "parameters must be a list"),
    ],
)
def test_invalid_contract_metadata_is_rejected(tmp_path, edit, message):
    descriptor = _write_dataset(tmp_path / "dataset")
    _edit_descriptor(descriptor, edit)
    with pytest.raises(DatasetContractError, match=message):
        open_dataset(descriptor)
    assert validate_dataset(descriptor)["status"] == "FAIL"


def test_missing_sample_and_checksum_mismatch(tmp_path):
    descriptor = _write_dataset(tmp_path / "missing")
    (descriptor.parent / "sample_001.npz").unlink()
    report = validate_dataset(descriptor)
    assert report["status"] == "FAIL"
    assert any("missing referenced file" in error for error in report["errors"])

    descriptor = _write_dataset(tmp_path / "checksum")
    with (descriptor.parent / "sample_000.npz").open("ab") as stream:
        stream.write(b"changed")
    report = validate_dataset(descriptor)
    assert report["status"] == "FAIL"
    assert any("checksum mismatch" in error for error in report["errors"])


def test_sample_parameter_must_match_declared_values(tmp_path):
    descriptor = _write_dataset(tmp_path / "parameters")
    _edit_descriptor(
        descriptor,
        lambda payload: payload["samples"][0]["parameters"].update(reynolds_number=999),
    )
    report = validate_dataset(descriptor)
    assert report["status"] == "FAIL"
    assert any("not in declared values" in error for error in report["errors"])


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("missing_array", "missing arrays"),
        ("nonfinite", "NaN or Inf"),
        ("field_shape", "field pressure shape mismatch"),
        ("connectivity", "connectivity indices are out of bounds"),
        ("shared_geometry", "shared geometry mismatch"),
    ],
)
def test_npz_payload_validation(tmp_path, defect, message):
    descriptor = _write_dataset(tmp_path / defect, defect=defect)
    report = validate_dataset(descriptor)
    assert report["status"] == "FAIL"
    assert any(message in error for error in report["errors"])


def test_dataset_cli_human_json_and_invalid_path(tmp_path, capsys):
    descriptor = _write_dataset(tmp_path / "dataset")
    assert main(["dataset", "info", str(descriptor.parent)]) == 0
    assert "Dataset Contract v1" in capsys.readouterr().out
    assert main(["dataset", "info", str(descriptor), "--json"]) == 0
    assert '"dataset_id": "test/tiny-cavity"' in capsys.readouterr().out
    assert main(["dataset", "validate", str(descriptor.parent)]) == 0
    assert "Dataset structure and payload: PASS" in capsys.readouterr().out
    assert main(["dataset", "validate", str(descriptor), "--json"]) == 0
    assert '"status": "PASS"' in capsys.readouterr().out
    assert main(["dataset", "info", str(tmp_path / "missing")]) == 2
    assert "missing dataset descriptor" in capsys.readouterr().err
    assert main(["dataset", "validate", str(tmp_path / "missing")]) == 1
    assert "Dataset structure and payload: FAIL" in capsys.readouterr().out
