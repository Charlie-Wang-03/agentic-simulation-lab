"""Dataset Contract v1 reader and validator.

The descriptor and metadata path use only the Python standard library. NumPy is
imported lazily when a sample is loaded or its numerical payload is validated.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

SCHEMA_VERSION = 1
DESCRIPTOR_NAME = "dataset.json"
_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "dataset_id",
    "name",
    "source",
    "representation",
    "parameters",
    "fields",
    "geometry",
    "samples",
    "provenance",
    "validation",
    "splits",
}


class DatasetContractError(ValueError):
    """Raised when a dataset descriptor or payload violates Contract v1."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _descriptor_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate / DESCRIPTOR_NAME if candidate.is_dir() else candidate


def _read_descriptor(path: str | Path) -> tuple[Path, dict[str, Any]]:
    descriptor = _descriptor_path(path)
    try:
        payload = json.loads(descriptor.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetContractError(f"missing dataset descriptor: {descriptor}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DatasetContractError(f"malformed dataset descriptor: {descriptor}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DatasetContractError("dataset descriptor must be a JSON object")
    return descriptor.resolve(), payload


def _portable_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    return not posix.is_absolute() and not windows.is_absolute() and ".." not in posix.parts


def _resolve_payload_path(root: Path, value: object) -> Path:
    if not _portable_path(value):
        raise DatasetContractError(f"dataset payload path must be portable and relative: {value!r}")
    candidate = (root / str(value)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise DatasetContractError(f"dataset payload path escapes dataset root: {value!r}") from exc
    return candidate


def _metadata_errors(metadata: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = _REQUIRED_TOP_LEVEL - metadata.keys()
    if missing:
        errors.append(f"descriptor missing fields: {sorted(missing)}")
    if metadata.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"unsupported dataset schema_version: {metadata.get('schema_version')!r}")
    for name in ("dataset_id", "name"):
        if not isinstance(metadata.get(name), str) or not metadata.get(name):
            errors.append(f"{name} must be a non-empty string")
    for name in ("source", "representation", "geometry", "provenance", "validation", "splits"):
        if not isinstance(metadata.get(name), dict):
            errors.append(f"{name} must be an object")
    source = metadata.get("source")
    if isinstance(source, dict):
        for name in ("case", "physics_domain"):
            if not isinstance(source.get(name), str) or not source.get(name):
                errors.append(f"source.{name} must be a non-empty string")
    representation = metadata.get("representation")
    if isinstance(representation, dict):
        for name in ("kind", "mesh", "temporal"):
            if not isinstance(representation.get(name), str) or not representation.get(name):
                errors.append(f"representation.{name} must be a non-empty string")

    parameters = metadata.get("parameters")
    parameter_items = parameters if isinstance(parameters, list) else []
    if not isinstance(parameters, list):
        errors.append("parameters must be a list")
    else:
        seen: set[str] = set()
        for item in parameters:
            if not isinstance(item, dict):
                errors.append("each parameter must be an object")
                continue
            missing_parameter = {"name", "units", "meaning", "provenance"} - item.keys()
            if missing_parameter:
                errors.append(f"parameter missing fields: {sorted(missing_parameter)}")
            name = item.get("name")
            if not isinstance(name, str) or not name:
                errors.append("parameter name must be a non-empty string")
            elif name in seen:
                errors.append(f"duplicate parameter: {name}")
            else:
                seen.add(name)
            if "values" not in item and "range" not in item:
                errors.append(f"parameter {name!r} must declare values or range")
            if "values" in item and (not isinstance(item["values"], list) or not item["values"]):
                errors.append(f"parameter {name!r} values must be a non-empty list")
            if "range" in item and (
                not isinstance(item["range"], list)
                or len(item["range"]) != 2
                or not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in item["range"])
                or item["range"][0] > item["range"][1]
            ):
                errors.append(f"parameter {name!r} range must be an ordered numeric pair")
            for required_text in ("units", "meaning", "provenance"):
                if not isinstance(item.get(required_text), str) or not item.get(required_text):
                    errors.append(f"parameter {name!r} {required_text} must be a non-empty string")

    fields = metadata.get("fields")
    if not isinstance(fields, list) or not fields:
        errors.append("fields must be a non-empty list")
    else:
        seen_fields: set[str] = set()
        for field in fields:
            if not isinstance(field, dict):
                errors.append("each field must be an object")
                continue
            missing_field = {"name", "units", "location", "dtype", "shape"} - field.keys()
            if missing_field:
                errors.append(f"field missing fields: {sorted(missing_field)}")
            name = field.get("name")
            if not isinstance(name, str) or not name:
                errors.append("field name must be a non-empty string")
            elif name in seen_fields:
                errors.append(f"duplicate field: {name}")
            else:
                seen_fields.add(name)
            if not isinstance(field.get("shape"), list) or not field.get("shape"):
                errors.append(f"field {name!r} shape must be a non-empty list")
            for required_text in ("units", "location", "dtype"):
                if not isinstance(field.get(required_text), str) or not field.get(required_text):
                    errors.append(f"field {name!r} {required_text} must be a non-empty string")

    geometry = metadata.get("geometry")
    if isinstance(geometry, dict):
        for name in ("coordinates", "connectivity"):
            spec = geometry.get(name)
            if not isinstance(spec, dict):
                errors.append(f"geometry.{name} must be an object")
                continue
            required_geometry = {"array", "dtype", "shape"}
            if name == "coordinates":
                required_geometry.add("units")
            missing_geometry = required_geometry - spec.keys()
            if missing_geometry:
                errors.append(f"geometry.{name} missing fields: {sorted(missing_geometry)}")
            for required_text in ({"array", "dtype", "units"} if name == "coordinates" else {"array", "dtype"}):
                if not isinstance(spec.get(required_text), str) or not spec.get(required_text):
                    errors.append(f"geometry.{name}.{required_text} must be a non-empty string")
            if not isinstance(spec.get("shape"), list) or not spec.get("shape"):
                errors.append(f"geometry.{name}.shape must be a non-empty list")
        if not isinstance(geometry.get("shared"), bool):
            errors.append("geometry.shared must be a boolean")
        if (
            not isinstance(geometry.get("dimensionality"), int)
            or isinstance(geometry.get("dimensionality"), bool)
            or geometry.get("dimensionality", 0) <= 0
        ):
            errors.append("geometry.dimensionality must be a positive integer")

    samples = metadata.get("samples")
    parameter_names = {
        item.get("name") for item in parameter_items if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    parameter_specs = {
        item["name"]: item for item in parameter_items if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if not isinstance(samples, list) or not samples:
        errors.append("samples must be a non-empty list")
    else:
        seen_samples: set[str] = set()
        for sample in samples:
            if not isinstance(sample, dict):
                errors.append("each sample must be an object")
                continue
            sample_id = sample.get("id")
            if not isinstance(sample_id, str) or not sample_id:
                errors.append("sample id must be a non-empty string")
            elif sample_id in seen_samples:
                errors.append(f"duplicate sample id: {sample_id}")
            else:
                seen_samples.add(sample_id)
            values = sample.get("parameters")
            if not isinstance(values, dict):
                errors.append(f"sample {sample_id!r} parameters must be an object")
            elif parameter_names - values.keys():
                errors.append(f"sample {sample_id!r} missing parameters: {sorted(parameter_names - values.keys())}")
            else:
                for parameter_name, value in values.items():
                    spec = parameter_specs.get(parameter_name)
                    if spec is None:
                        errors.append(f"sample {sample_id!r} declares unknown parameter: {parameter_name}")
                        continue
                    declared_values = spec.get("values")
                    declared_range = spec.get("range")
                    if isinstance(declared_values, list) and value not in declared_values:
                        errors.append(f"sample {sample_id!r} parameter {parameter_name!r} is not in declared values")
                    if (
                        isinstance(declared_range, list)
                        and len(declared_range) == 2
                        and all(
                            isinstance(bound, (int, float)) and not isinstance(bound, bool) for bound in declared_range
                        )
                        and isinstance(value, (int, float))
                        and not declared_range[0] <= value <= declared_range[1]
                    ):
                        errors.append(f"sample {sample_id!r} parameter {parameter_name!r} is outside declared range")
            files = sample.get("files")
            if not isinstance(files, list) or not files:
                errors.append(f"sample {sample_id!r} files must be a non-empty list")
            else:
                for reference in files:
                    if (
                        not isinstance(reference, dict)
                        or not _portable_path(reference.get("path"))
                        or not isinstance(reference.get("format"), str)
                    ):
                        errors.append(f"sample {sample_id!r} has an unsafe or malformed file reference")

    provenance = metadata.get("provenance")
    if isinstance(provenance, dict):
        for name in ("generator", "source_case"):
            if not isinstance(provenance.get(name), str) or not provenance.get(name):
                errors.append(f"provenance.{name} must be a non-empty string")
        solver = provenance.get("solver")
        if not isinstance(solver, dict):
            errors.append("provenance.solver must be an object")
        else:
            for name in ("name", "observed_version"):
                if not isinstance(solver.get(name), str) or not solver.get(name):
                    errors.append(f"provenance.solver.{name} must be a non-empty string")
        if not isinstance(provenance.get("packages"), dict):
            errors.append("provenance.packages must be an object")
        if not isinstance(provenance.get("generation_configuration"), dict):
            errors.append("provenance.generation_configuration must be an object")

    validation = metadata.get("validation")
    if isinstance(validation, dict):
        for name in ("status", "schema_reload", "numerical_finiteness", "shape_topology_consistency", "physics"):
            if name not in validation:
                errors.append(f"validation missing field: {name}")
        if not isinstance(validation.get("physics"), dict):
            errors.append("validation.physics must be an object")
        else:
            for name in ("status", "basis", "source_case"):
                if not isinstance(validation["physics"].get(name), str) or not validation["physics"].get(name):
                    errors.append(f"validation.physics.{name} must be a non-empty string")
    splits = metadata.get("splits")
    if isinstance(splits, dict):
        if not isinstance(splits.get("official"), bool):
            errors.append("splits.official must be a boolean")
        if not isinstance(splits.get("semantics"), str) or not splits.get("semantics"):
            errors.append("splits.semantics must be a non-empty string")
    return errors


@dataclass(frozen=True)
class Dataset:
    """An opened Dataset Contract v1 descriptor."""

    descriptor_path: Path
    metadata: dict[str, Any]

    @property
    def root(self) -> Path:
        return self.descriptor_path.parent

    def __len__(self) -> int:
        return len(self.metadata["samples"])

    def load_sample(self, index: int | str) -> dict[str, Any]:
        """Load one NPZ sample with ``allow_pickle=False`` and return its arrays."""
        if isinstance(index, str):
            sample = next((item for item in self.metadata["samples"] if item["id"] == index), None)
            if sample is None:
                raise DatasetContractError(f"unknown sample id: {index}")
        else:
            try:
                sample = self.metadata["samples"][index]
            except IndexError as exc:
                raise DatasetContractError(f"sample index out of range: {index}") from exc
        reference = next((item for item in sample["files"] if item.get("format") == "npz"), sample["files"][0])
        path = _resolve_payload_path(self.root, reference["path"])
        try:
            import numpy as np
        except ImportError as exc:
            raise DatasetContractError("NumPy is required to load samples; install the 'data' extra") from exc
        required = {
            self.metadata["geometry"]["coordinates"]["array"],
            self.metadata["geometry"]["connectivity"]["array"],
            *(field["name"] for field in self.metadata["fields"]),
        }
        try:
            with np.load(path, allow_pickle=False) as archive:
                missing = required - set(archive.files)
                if missing:
                    raise DatasetContractError(f"{reference['path']}: missing arrays: {sorted(missing)}")
                arrays = {name: np.asarray(archive[name]).copy() for name in required}
        except DatasetContractError:
            raise
        except (OSError, ValueError) as exc:
            raise DatasetContractError(f"cannot safely load {reference['path']}: {exc}") from exc
        return {**arrays, "sample_id": sample["id"], "parameters": dict(sample["parameters"])}

    def validate(self, *, check_data: bool = True) -> dict[str, Any]:
        """Validate this dataset without changing its declared physics evidence."""
        return validate_dataset(self.descriptor_path, check_data=check_data)


def open_dataset(path: str | Path) -> Dataset:
    """Open a dataset folder or descriptor without importing NumPy."""
    descriptor, metadata = _read_descriptor(path)
    errors = _metadata_errors(metadata)
    if errors:
        raise DatasetContractError("; ".join(errors))
    return Dataset(descriptor, metadata)


def _file_references(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    samples = metadata.get("samples", [])
    if isinstance(samples, list):
        for sample in samples:
            if not isinstance(sample, dict) or not isinstance(sample.get("files"), list):
                continue
            references.extend(item for item in sample["files"] if isinstance(item, dict))
    supporting = metadata.get("supporting_files", [])
    if isinstance(supporting, list):
        references.extend(item for item in supporting if isinstance(item, dict))
    return references


def _shape_tuple(shape: list[object], dimensions: dict[str, int]) -> tuple[int, ...] | None:
    resolved: list[int] = []
    for item in shape:
        if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
            resolved.append(item)
        elif isinstance(item, str) and item in dimensions:
            resolved.append(dimensions[item])
        else:
            return None
    return tuple(resolved)


def validate_dataset(path: str | Path, *, check_data: bool = True) -> dict[str, Any]:
    """Validate Dataset Contract v1 structure and, by default, numerical payloads."""
    errors: list[str] = []
    try:
        descriptor, metadata = _read_descriptor(path)
    except DatasetContractError as exc:
        return {"status": "FAIL", "errors": [str(exc)], "physics_validation": None}
    errors.extend(_metadata_errors(metadata))
    root = descriptor.parent
    for reference in _file_references(metadata):
        try:
            payload_path = _resolve_payload_path(root, reference.get("path"))
        except DatasetContractError as exc:
            errors.append(str(exc))
            continue
        if not payload_path.is_file():
            errors.append(f"missing referenced file: {reference.get('path')}")
            continue
        checksum = reference.get("sha256")
        if checksum is not None and (not isinstance(checksum, str) or sha256_file(payload_path) != checksum.lower()):
            errors.append(f"checksum mismatch: {reference.get('path')}")

    if check_data and not errors:
        try:
            import numpy as np
        except ImportError:
            errors.append("NumPy is required for payload validation; install the 'data' extra")
        else:
            geometry = metadata["geometry"]
            coordinate_name = geometry["coordinates"]["array"]
            connectivity_name = geometry["connectivity"]["array"]
            shared_coordinates = None
            shared_connectivity = None
            for sample_number, sample in enumerate(metadata["samples"]):
                try:
                    loaded = Dataset(descriptor, metadata).load_sample(sample_number)
                    coordinates = loaded[coordinate_name]
                    connectivity = loaded[connectivity_name]
                    dimensionality = geometry["dimensionality"]
                    if coordinates.ndim != 2 or coordinates.shape[1] != dimensionality:
                        errors.append(f"{sample['id']}: coordinate dimensions do not match dimensionality")
                    if connectivity.ndim != 2:
                        errors.append(f"{sample['id']}: connectivity must be two-dimensional")
                    if coordinates.dtype != np.dtype(geometry["coordinates"]["dtype"]):
                        errors.append(f"{sample['id']}: coordinates dtype mismatch")
                    if connectivity.dtype != np.dtype(geometry["connectivity"]["dtype"]):
                        errors.append(f"{sample['id']}: connectivity dtype mismatch")
                    numeric_arrays = [coordinates, connectivity, *(loaded[field["name"]] for field in metadata["fields"])]
                    if not all(np.isfinite(array).all() for array in numeric_arrays):
                        errors.append(f"{sample['id']}: numerical arrays contain NaN or Inf")
                    if connectivity.size == 0 or connectivity.min() < 0 or connectivity.max() >= len(coordinates):
                        errors.append(f"{sample['id']}: connectivity indices are out of bounds")
                    dimensions = {"node": len(coordinates), "cell": len(connectivity)}
                    expected_coordinates = _shape_tuple(geometry["coordinates"]["shape"], dimensions)
                    expected_connectivity = _shape_tuple(geometry["connectivity"]["shape"], dimensions)
                    if expected_coordinates is None:
                        errors.append(f"{sample['id']}: coordinates shape semantics are invalid")
                    elif coordinates.shape != expected_coordinates:
                        errors.append(f"{sample['id']}: coordinates shape mismatch")
                    if expected_connectivity is None:
                        errors.append(f"{sample['id']}: connectivity shape semantics are invalid")
                    elif connectivity.shape != expected_connectivity:
                        errors.append(f"{sample['id']}: connectivity shape mismatch")
                    for field in metadata["fields"]:
                        array = loaded[field["name"]]
                        expected = _shape_tuple(field["shape"], dimensions)
                        if expected is None or array.shape != expected:
                            errors.append(f"{sample['id']}: field {field['name']} shape mismatch")
                        if array.dtype != np.dtype(field["dtype"]):
                            errors.append(f"{sample['id']}: field {field['name']} dtype mismatch")
                    if geometry["shared"]:
                        if shared_coordinates is None:
                            shared_coordinates = coordinates.copy()
                            shared_connectivity = connectivity.copy()
                        elif not np.array_equal(shared_coordinates, coordinates) or not np.array_equal(
                            shared_connectivity, connectivity
                        ):
                            errors.append(f"{sample['id']}: shared geometry mismatch")
                except (DatasetContractError, TypeError, ValueError) as exc:
                    errors.append(f"{sample.get('id', sample_number)}: {exc}")

    physics = metadata.get("validation", {}).get("physics") if isinstance(metadata.get("validation"), dict) else None
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not errors else "FAIL",
        "descriptor": descriptor.name,
        "dataset_id": metadata.get("dataset_id"),
        "sample_count": len(metadata.get("samples", [])) if isinstance(metadata.get("samples"), list) else 0,
        "checks": {
            "contract_metadata": not _metadata_errors(metadata),
            "referenced_files": not any("referenced file" in error for error in errors),
            "checksums": not any("checksum mismatch" in error for error in errors),
            "numerical_payload": check_data and not errors,
        },
        "physics_validation": physics,
        "errors": errors,
    }
