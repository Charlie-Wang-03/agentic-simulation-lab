# Run and validate

## When to use

Use for an authorized benchmark, dataset generator, or suite execution.

## Preconditions

Run `list`, exact `info`, and `doctor`; confirm solver/license impact and timeout.

## Main commands

Run the exact `agentic-sim run <domain> --case <slug> --dry-run` first. Execute
only the reviewed selection. Then run `agentic-sim validate <domain> --case
<slug>` and inspect the routed run record.

## Evidence source

The manifest schema v2 `result_file` plus Canonical Case Result Contract v1 (or
the explicitly declared single legacy adapter) is authoritative. `run.json`, stdout,
stderr, plots, and other JSON are supporting evidence only.

For dataset generators, `dataset.json` is the Dataset Contract v1 authority for
portable data. Its PASS cannot replace generator or source-case physics evidence.

## Stop conditions

Stop on a failed dry run, missing authorization/license, timeout, invalid/missing
authoritative result, or declared physics failure. A retry needs a distinct written
hypothesis and must preserve the prior run.

## Forbidden shortcuts

Never infer PASS from exit zero, scan arbitrary JSON for status, relax acceptance
thresholds, delete failure evidence, or rerun indefinitely.

## Expected output

Process outcome, result-contract outcome, physics checks, normalized final status,
project-relative run/result/log paths, hypothesis if rerun, and evidence freshness.
