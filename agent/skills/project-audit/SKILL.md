# Project audit

## When to use

Use after project changes and for a frozen public-export candidate.

## Preconditions

Identify the exact tree root. Publication candidates must come from a versioned
revision and be audited as the exported tree, not inferred from the private source.

## Main commands

Run compileall, Ruff, pytest, catalog/project/reference freshness, static self-test,
public-tree/privacy, dataset portability, subprocess policy, documentation links,
tutorial pairing, lazy-import safety, result/dataset contract tests, representative
non-solver CLI commands, and `git diff --check`. Use `python tools/check_public_tree.py
--root <export>` for an exported candidate and `tools/release_audit.py` only for the
broader maintainer-controlled readiness decision.

## Evidence source

Command return codes and reports, manifest/result contracts, the actual target tree,
and preserved historical solver evidence.

## Stop conditions

Any static failure, prohibited/private file, generated/proprietary artifact, broken
contract/link, unresolved status, or missing maintainer LICENSE decision prevents a
publication-ready claim.

## Forbidden shortcuts

Do not audit only the mother working tree, copy ignored/local state, hide FAIL or
BLOCKED cases, create a public repository, choose a LICENSE, or call structural
dataset validity physics PASS.

## Expected output

Per-gate results, unresolved status counts, exported-tree hash/file list when
applicable, and explicit manual publication blockers.
