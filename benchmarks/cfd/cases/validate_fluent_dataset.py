"""Reload and validate the Fluent flagship Dataset Contract v1 payload."""

from __future__ import annotations

from fluent_smoke_common import OUT, write_json

from agentic_simulation_lab.datasets import validate_dataset


def main() -> int:
    folder = OUT / "fluent_dataset"
    result = validate_dataset(folder)
    write_json(folder / "dataset_validation.json", result)
    print(result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
