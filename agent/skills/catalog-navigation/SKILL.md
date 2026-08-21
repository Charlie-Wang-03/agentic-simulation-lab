# Catalog navigation

## When to use

Use to discover domains, cases, declared status, and historical evidence.

## Preconditions

None; this workflow is solver-independent.

## Main commands

1. Run `agentic-sim list`, optionally with `--domain`, `--role`, or `--status`.
2. Use `info <domain> [case]` for the manifest record.

## Evidence source

Manifest schema v2 and the referenced historical evidence. `doctor` is current
environment evidence and does not rewrite catalog history.

## Stop conditions

Stop on an unknown domain/case or invalid manifest; do not guess a slug.

## Forbidden shortcuts

Never describe `NOT_RUN` as unsupported, `BLOCKED` as failed physics, or a
historical PASS as a fresh validation.

## Expected output

The exact domain/case slug, role, declared status, evidence path, authoritative
`result_file`, result format, and whether evidence is historical or fresh.
