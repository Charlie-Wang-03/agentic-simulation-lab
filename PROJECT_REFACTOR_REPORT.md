# Agentic Simulation Lab refactor report

Date: 2026-08-16 (post-rename verification updated 2026-08-21)

## 1. Original state

The workspace began as a flat solver-automation collection with 178 root Python/Markdown sources and reports, plus large `outputs/` and `logs/` trees. The baseline inventory recorded 7,529 files and about 1.02 GB. No Git repository existed. Existing suite summaries contained successful, failed, and product-blocked cases that required preservation.

## 2. New architecture

The public identity is **Agentic Simulation Lab** (`agentic-simulation-lab`). Source, benchmarks, agent guidance, documentation, tests, tools, references, and ignored artifacts now have separate ownership. The import-safe `src/agentic_simulation_lab` package contains a solver-independent core and lazy solver adapters.

## 3. Files moved

The deterministic migration receipt records 165 source/common/runner moves into domain ownership. Large artifacts were moved, not copied. Flat root solver scripts were eliminated; only public project and engineering files remain at root.

## 4. Domains

Eleven manifests cover mechanics, thermal, CFD, multiphysics, materials, electromagnetics, acoustics, porous media/geomechanics, DEM, SPH, and phase-change/reactive flow. Each domain has cases, common helpers, a suite entrypoint, compact references, README, and manifest metadata for solver, analysis, entrypoint, status, and evidence.

## 5. CLI

The `agentic-sim` console script implements `doctor`, `list`, `info`, `run`, `validate`, `audit`, `report`, and `paths`. It was built and installed in an isolated temporary environment and its discovery, information, reporting, auditing, and path commands passed. `run --dry-run` passed. Execution classifies result JSON physics status rather than equating exit code zero with PASS, and routes outputs, datasets, and logs under `artifacts/`.

## 6. Agent layer

`AGENTS.md` defines the API-first workflow, physical-validation requirement, failure semantics, evidence handling, and modification rules. `agent/` supplies vendor-neutral workflow/protocol/policy documents and reusable skills for new benchmarks, execution/validation, solver diagnosis, physics validation, and project audit.

## 7. Documentation

English and Chinese landing pages provide equivalent architecture, CLI, validation, dataset, learning-path, status, contribution, and disclaimer guidance. Five required tutorial pairs cover quick start, agent-first operation, benchmark execution, dataset generation, and adding a benchmark. English project vision, architecture, domains, solver matrix, datasets, development, migration, metrics, showcase, limitations, reports, and release checklist are present.

## 8. CI and open-source engineering

The repository includes GitHub static CI, issue/PR templates, pre-commit configuration, packaging metadata, contribution/conduct/security/changelog/disclaimer files, attributes, editor settings, and comprehensive ignores. LICENSE selection and confirmed citation-author metadata remain deliberate maintainer decisions; no license or author identity was guessed.

## 9. Tests

Eight pytest modules cover imports, manifests, registry/catalog, CLI, paths, statuses, references, and the public tree. All 13 pytest tests passed. Ruff passed with no findings across `src`, `tests`, and `tools`. The dependency-free local self-test passed, all Python compiled, manifest/catalog validation passed, link checking passed, and the installed console CLI passed. Pytest and Ruff were executed from verified local offline package caches; no downloads were required.

## 10. Artifact migration

The verified receipt contains 6,930 output files totaling 981,020,535 bytes and 250 log files totaling 41,839,639 bytes. Source and destination counts/bytes match exactly. Local legacy artifacts are ignored while `artifacts/README.md` remains public. All 283 historical JSON files and 91 NPZ files revalidated; three documented missing-data qualifications are retained for SPH rather than silently replaced.

## 11. Benchmark status

The generated catalog contains 11 domains and 134 entries: **123 PASS, 4 FAIL, 4 BLOCKED, and 3 NOT_RUN**. Roles comprise 113 benchmarks, 9 dataset generators, and 12 utilities. Statuses come from sanitized suite summaries, current release regressions, or checksum-backed exact-name historical results.

## 12. Known failures

- Premixed combustion Case G remains FAIL after both permitted diagnostics. The first retained good conservation/temperature but an upstream reaction peak; the second added temperature clipping, reverse flow, and carbon imbalance.
- Reactive CHT Case J remains FAIL after its corrected retest: seven checks passed, but total-enthalpy closure error was 15.95% against the unchanged 10% limit.
- The current AEDT electrostatic regression remains FAIL because the supported PyAEDT gRPC session did not start after trusted official Student discovery.
- The Turek–Hron FSI case retains its historical FAIL.
- Four entries remain BLOCKED by observed Student product modes or current APIs; they were normalized without erasing the limitation.

## 13. Open-source blockers

Public release still requires maintainer decisions for LICENSE selection and citation-author metadata. Solver products and licenses are external prerequisites and are not redistributed.

## 14. Public identity status

The public software identity is `agentic-simulation-lab`. The private R&D mother repository retains its historical private directory/repository identity; public packages, commands, URLs, and clean exports do not depend on that name. No duplicate public project tree or copied Git history is created.

## 15. Final validation status

PASS after rename: compile, pytest (13 tests), Ruff, dependency-free self-test, manifest validation, catalog freshness, installed CLI smoke, historical JSON/NPZ revalidation, artifact count/byte preservation, link check, ignore verification, public-tree audit, package build/content inspection, clean-wheel smoke, and four representative solver regressions. FAIL evidence is retained for Case J physics closure and AEDT supported-session startup. Git was initialized; nothing was staged, committed, pushed, or connected to a remote.
