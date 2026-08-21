# Agent workflow

Use one evidence-preserving sequence:

```text
discover → diagnose → dry-run → execute → inspect authoritative result
         → physics validate → classify → preserve evidence → audit
```

The manifest schema v2 `result_file` and its declared result format identify the
only authoritative execution result. For migrated cases, the legacy adapter reads
that exact file; agents never scan arbitrary JSON or infer physics success from a
zero process exit.

`dataset.json` is the authority for Dataset Contract v1 structure and payloads.
Dataset validation PASS does not imply the source case or generator physics PASS;
that evidence remains separate in the Canonical Case Result Contract v1 result.

Use only `PASS`, `FAIL`, `BLOCKED`, `PARTIAL`, and `NOT_RUN`. Preserve historical
evidence separately from fresh runs, prefer supported APIs and scripting over GUI
automation, and stop at the narrowest evidenced failure layer.
