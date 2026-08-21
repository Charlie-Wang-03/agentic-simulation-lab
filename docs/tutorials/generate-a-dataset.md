# Generate and reload a dataset

This tutorial follows the flagship Scientific-AI path:

```text
discover → inspect → dry-run → generate → inspect contract → reload sample → validate
```

The example is a 12-sample educational smoke dataset, not a training-scale benchmark. It demonstrates how validated simulation output becomes portable structured data; it does not train a model.

## 1. Discover and inspect

```bash
agentic-sim list --role dataset
agentic-sim info cfd fluent-parametric-dataset
```

The source physics is a steady, laminar, two-dimensional lid-driven cavity. The deterministic sweep uses Reynolds numbers 100–1200, one shared 40 × 40 quadrilateral mesh, and nodal `velocity_x`, `velocity_y`, and `pressure`.

## 2. Dry-run first

```bash
agentic-sim run cfd --case fluent-parametric-dataset --dry-run
agentic-sim run cfd --case fluent-parametric-dataset --dry-run --json
```

Dry-run returns `NOT_RUN` and creates no artifacts. JSON output exposes the planned `output_directory`, timeout, entrypoint, and authoritative Case Result path.

## 3. Generate only in an authorized solver environment

The following command starts Fluent 12 times. Run it only when that execution is explicitly intended and a compatible Fluent product/license is available:

```bash
agentic-sim run cfd --case fluent-parametric-dataset --json
```

The returned `output_directory` has this form:

```text
artifacts/datasets/cfd/fluent-parametric-dataset/<UTC timestamp>
```

The portable dataset root is its `fluent_dataset/` child. Local proprietary solver evidence, if written, stays outside that portable directory under `solver-evidence/`.

## 4. Inspect Dataset Contract v1

Let `<dataset-path>` mean the generated `.../<timestamp>/fluent_dataset` directory.

```bash
agentic-sim dataset info <dataset-path>
agentic-sim dataset info <dataset-path> --json
```

`<dataset-path>/dataset.json` is the authoritative dataset descriptor. It records identity, representation, parameters, fields and units, mesh semantics, sample-to-file mappings, SHA-256 checksums, requested/observed provenance, validation evidence, and split semantics. `dataset_index.csv` and `dataset_validation.json` are supporting artifacts.

## 5. Reload one NumPy sample

Install the existing data extra if needed:

```bash
python -m pip install -e ".[data]"
```

Then load through the package API:

```python
from agentic_simulation_lab.datasets import open_dataset

dataset = open_dataset("<dataset-path>")
print(dataset.metadata["source"])
print(dataset.metadata["parameters"])
print(dataset.metadata["fields"])

sample = dataset.load_sample(0)
print(sample["sample_id"], sample["parameters"])
print(sample["coordinates"].shape)
print(sample["connectivity"].shape)
print(sample["velocity_x"].shape)
print(sample["velocity_y"].shape)
print(sample["pressure"].shape)
```

The reader always calls NumPy with `allow_pickle=False`.

## 6. Validate structure and payload

```bash
agentic-sim dataset validate <dataset-path>
agentic-sim dataset validate <dataset-path> --json
```

Validation checks the contract, safe relative paths, referenced files, checksums, required arrays, finiteness, dtypes, shapes, connectivity bounds, parameter alignment, and shared geometry. Its `status` describes dataset structure and payload only. The separate `physics_validation` member reports the declared source-case evidence and is never inferred from file validity.

The NPZ files are ready to feed into a downstream surrogate or neural-operator pipeline, but this repository stops before ML training. Twelve samples and no official train/validation/test split are intentionally insufficient grounds for training-quality claims.
