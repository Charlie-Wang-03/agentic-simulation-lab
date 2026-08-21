# Datasets

The dataset layer turns validated simulation output into portable structured data. It does not train machine-learning models.

## Two separate contracts

| Contract | Authoritative file | Question answered |
|---|---|---|
| Canonical Case Result Contract v1 | the manifest's `result_file`, normally `case-result.json` | Did this generator execution PASS, FAIL, or become BLOCKED? |
| Dataset Contract v1 | `dataset.json` at the portable dataset root | What data was produced, how is it represented, and can it be safely loaded and checked? |

A dataset validator never upgrades file validity into physics `PASS`. The descriptor retains the source case and the declared physics-evidence basis separately.

## Dataset Contract v1

`dataset.json` is the only authoritative dataset-level descriptor. CSV indices, per-sample embedded metadata, plots, and `dataset_validation.json` are supporting files.

The required top-level members are:

- `schema_version`, `dataset_id`, and `name`;
- `source`: source catalog case, physics domain, and problem identity;
- `representation`: a small description such as Eulerian/Lagrangian, structured/unstructured, and steady/temporal;
- `parameters`: name, units, meaning, declared values or range, and sample provenance;
- `fields`: name, units, location, dtype, and symbolic shape;
- `geometry`: coordinate and connectivity array names, dtypes, shapes, dimensionality, and shared/per-sample semantics;
- `samples`: stable sample id, parameter mapping, and one or more payload file references;
- `provenance`: generator, source case, solver requested/observed version, relevant package versions, and generation configuration;
- `validation`: dataset structure/reload checks plus a separate physics-evidence record;
- `splits`: whether an official split exists and what it means.

The current version deliberately avoids a large representation hierarchy. It supports the flagship steady shared-mesh Eulerian NPZ workflow while leaving explicit representation metadata for future transient, unstructured, or Lagrangian extensions.

## Portability and integrity

Every payload and supporting-file path is relative to the directory containing `dataset.json`, uses forward slashes, and may not be absolute or contain `..`. Resolution is checked again to prevent path escape. Portable payloads use open formats such as JSON, CSV, SVG, and compressed NPZ; they do not depend on proprietary solver project/database files.

File references may carry SHA-256 checksums. The generic validator checks path safety, existence, checksums, required arrays, safe NumPy loading with `allow_pickle=False`, finiteness, declared dtypes/shapes, coordinate dimensionality, connectivity bounds, shared-geometry identity, and sample-parameter alignment.

## Python reader

Metadata inspection uses only the Python standard library. NumPy is imported only by `load_sample` or deep payload validation, so the core package remains import-safe without the `data` extra.

```python
from agentic_simulation_lab.datasets import open_dataset, validate_dataset

dataset = open_dataset("artifacts/datasets/.../fluent_dataset")
print(dataset.metadata["fields"])

sample = dataset.load_sample(0)
print(sample["parameters"])
print(sample["coordinates"].shape)
print(sample["velocity_x"].shape)

report = validate_dataset(dataset.descriptor_path)
assert report["status"] == "PASS"
```

Install `.[data]` before loading NPZ arrays.

## CLI

```bash
agentic-sim dataset info artifacts/datasets/.../fluent_dataset
agentic-sim dataset info artifacts/datasets/.../fluent_dataset --json
agentic-sim dataset validate artifacts/datasets/.../fluent_dataset
agentic-sim dataset validate artifacts/datasets/.../fluent_dataset --json
```

Human output reports structural/payload validity and declared physics evidence on separate lines. JSON output preserves the same distinction.

## Flagship dataset

`cfd/fluent-parametric-dataset` is a 12-sample, steady 2-D lid-driven-cavity Reynolds-number sweep on one shared 40 × 40 quadrilateral mesh. Each sample is a compressed NPZ containing `coordinates`, zero-based `connectivity`, `velocity_x`, `velocity_y`, and `pressure`. `dataset.json` links parameter values to files and checksums.

This is an educational smoke dataset and data-pipeline demonstration. It is machine-learning-ready in format, but it is not training-scale and has no official train/validation/test split. The portable dataset excludes the local Fluent `.cas.h5` evidence. See the bilingual [dataset tutorial](tutorials/generate-a-dataset.md).
