# Result validation

## When to use

Use to evaluate an authoritative result or proposed status change.

## Preconditions

Locate the manifest `result_file`, declared format, acceptance checks, units, and
control-volume/reference definition.

## Main commands

Validate the exact result through `agentic-sim validate <domain> --case <slug>`.
Independently check finiteness and units, then prefer analytical conservation,
canonical comparison, dimensional/limiting behavior, and finally expected trends.

## Evidence source

Canonical Case Result Contract v1 checks and metrics. Dataset Contract v1 provides
separate structural/payload evidence and never creates physics PASS.

## Stop conditions

Missing quantities, ambiguous signs/units, malformed result contract, or failed
physics checks stop validation with truthful `FAIL`/`PARTIAL`; unavailable required
capability is `BLOCKED`.

## Forbidden shortcuts

Do not loosen thresholds, accept plausible plots or exit zero, select a favorable
time window after seeing results, or overwrite historical FAIL/BLOCKED evidence.

## Expected output

Equation/reference, units, per-check result, residual/error, unchanged threshold,
normalized status, and project-relative evidence supporting any manifest change.
