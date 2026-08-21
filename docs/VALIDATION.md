# Validation policy

`PASS` requires an executed result and stated numerical or physical checks. `FAIL` means execution produced evidence that violates a required check. `BLOCKED` identifies an external product, license, API, or environment constraint. `PARTIAL` is reserved for deliberately incomplete coverage; `NOT_RUN` means no attributable evidence exists.

Changing a threshold requires an engineering justification and review. A failed case must not be made to pass by relaxing acceptance bounds. Dataset checks cover finiteness, schema, units, ordering, and domain-specific invariants. Historical references must be sanitized and project-relative.

## Canonical Case Result Contract v1

Executed benchmark and dataset cases have exactly one authoritative result file. Manifest schema v2 declares it explicitly. The default is `case-result.json`; migrated cases may declare one exact legacy path in their manifest. The executor does not recursively inspect other JSON files, so diagnostics and supporting metadata cannot overwrite physics status.

The v1 result requires `schema_version: 1`, a normalized `status`, `checks`, `metrics`, `artifacts`, and `provenance`. `run.json` is the execution envelope and records process failure, timeout, physics status, and contract errors separately. Missing or malformed authoritative results fail the run; process exit zero never implies physics `PASS`.

## Dataset validation is separate

Dataset Contract v1 uses `dataset.json` to describe generated data, not generator execution status. Its generic validator checks metadata, portable paths, checksums, safe NPZ reload, numerical finiteness, shapes, topology, and parameter alignment. The validator returns structural/payload status and carries declared source-case physics evidence in a separate `physics_validation` member; it never derives physics `PASS` from a well-formed file.
