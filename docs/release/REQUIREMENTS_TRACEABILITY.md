# Historical finalization requirement traceability

Checked: 2026-08-21

This dated matrix records the pre-integration finalization task and is not the current release-candidate report. In particular, its 13-test count and no-remote Git state are historical. Current catalog counts come from `docs/PROJECT_METRICS.md`; current solver limitations come from `docs/known-limitations.md`; actual remote CI must be verified from GitHub Actions for the exact candidate revision.

The matrix prevents partial static success from being mistaken for publication readiness. `artifacts/release/release_readiness.json` remains the machine-readable gate. Solver failures remain visible even when the execution path itself worked.

| Objective sections | Requirement group | Current state | Authoritative evidence |
|---|---|---|---|
| 0–1 | Baseline inventory and release freeze | PASS | Git/CLI inventory; changes limited to release-blocking fixes and release engineering |
| 2 | Official Ansys/GitHub source audit | PASS | `docs/release/OFFICIAL_SOURCE_AUDIT.md`, checked 2026-08-20 |
| 3–4 | Educational positioning and non-competitive benchmark definition | PASS | both READMEs; `docs/ANSYS_USAGE_AND_COMPLIANCE.md` |
| 5–8 | License separation, proprietary redistribution, copied examples, third-party notices | PASS | official-source audit; package-content scan; `THIRD_PARTY_NOTICES.md` |
| 9 | Preserve Case G | PASS | manifest/reference/report remain `FAIL`; no rerun performed |
| 10 | Corrected Case J retest | FAIL | historical final-step error 15.951% and fresh fixed-window error 15.842% both exceed the unchanged 10% limit |
| 11 | Mechanical/MAPDL, Fluent, AEDT, Rocky, System Coupling regressions | FAIL | four historical regressions pass; AEDT historical `FAIL` is preserved separately from fresh compatibility `BLOCKED`; `docs/release/SOLVER_REGRESSION_RESULTS.json` |
| 12–16 | Independent project environment | PASS | post-rename `.venv` editable install repaired; all six optional imports and `doctor` pass; `tools/bootstrap.py`, `environment.yml`, `docs/TESTED_ENVIRONMENTS.md` |
| 17–18 | Windows/macOS portability and accurate claims | PASS for core/config | Windows core smoke passes; macOS matrix configured; no local macOS solver claim |
| 19–21 | Bilingual project, Windows, macOS, Student, and AEDT installation tutorials | PASS | paired files under `docs/tutorials/`; link and pairing tools pass |
| 22, 38 | Cross-platform least-privilege static CI | PASS for configuration | `.github/workflows/ci.yml` parses and contains Windows/macOS/Ubuntu matrix, `contents: read`, no solver/secrets |
| 23–24 | Vendor-neutral, API-first agent contract | PASS | `AGENTS.md`, `agent/WORKFLOW.md`, English-only agent documentation |
| 25–27 | Subprocess, executable trust, network/environment safety | PASS | `docs/EXECUTION_SECURITY.md`; subprocess checker passes; insecure AEDT bypass removed |
| 28–31 | Privacy scanner, candidate-tree scope, publishing guidance | PASS | post-rename public-tree audit passes using Git ignore rules; bilingual publishing tutorial |
| 32–38 | CODEOWNERS, security/support, community/contribution templates, CI permissions | PASS | community files and release-audit gate pass |
| 39–40 | Repository LICENSE decision | PASS | maintainer-approved exact Apache-2.0 `LICENSE`; SPDX/package metadata; `docs/release/LICENSE_DECISION.md` |
| 41 | Citation identity | PASS | `CITATION.cff`; `cffconvert 2.0.0` schema 1.2.0 validation; `docs/release/CITATION_DECISION.md` |
| 42–43 | Trademark wording and Student limits | PASS | both READMEs; compliance/limits docs; official-source audit |
| 44–46 | README parity, tutorial pairing, English agent docs | PASS | manual parity review plus link/pairing checks; agent tree contains English documentation only |
| 47–48 | Dataset portability and public artifact thresholds | PASS | dataset-portability and public-tree checks pass; package contents pass |
| 49–51 | Neutral public identity, environment recreation, old-name search | PASS | public distribution/package/CLI/URLs use the neutral identity; private mother repository name is not exported |
| 52 | Git state | HISTORICAL SNAPSHOT | current private mother Git state must be checked directly; public export must contain no `.git` or private history |
| 53 | Full static pipeline | PASS | post-rename compile; 13/13 pytest; Ruff maintained scope; catalog/references/history/privacy/links/pairs/package checks |
| 54 | Clean-package smoke without solver integrations | PASS | post-rename wheel installed offline with `--no-deps` in a clean environment; `list`, `info`, `report`, `audit` pass |
| 55 | Windows project-environment solver smoke | PASS | Mechanical/MAPDL, Fluent, Rocky, and System Coupling real runs pass from project `.venv`; AEDT failure is separately retained |
| 56 | macOS CI smoke | NOT EVIDENCED IN THIS SNAPSHOT | local solver execution explicitly unvalidated; workflow configuration alone is not a remote PASS |
| 57–61 | Release audit, checklist, version, notes, GitHub metadata | PASS as preparation | release files exist; audit honestly returns NOT READY |
| 62–65 | Identity, onboarding clarity, restrained positioning | PASS | post-rename privacy/marketing scans pass; only `Charlie-Wang-03` remains |
| 66 | Final post-rename CLI/dry/optional real regression | PASS | `list`, `info`, `doctor`, and dependency-free dry-run self-test pass; existing real regression evidence retained without an unauthorized solver relaunch |
| 67 | Final catalog/metrics/report reconciliation | PASS | 11 domains/134 entries: 123 PASS, 4 FAIL, 4 BLOCKED, 3 NOT_RUN |
| 68–70 | Legal/compliance release gate and publication boundary | PASS as gate behavior | hard gates cover legal/IP/privacy/package/export integrity; truthful solver outcomes remain visible release qualifications |
| 71 | `FINALIZATION_REPORT.md` | PASS | reconciled to post-solver and post-rename evidence on 2026-08-21 |
| 72 | Final response | PASS | final technical handoff is supported by persisted evidence |
| 73 | Completion rule | SECOND GATE AUTHORIZED | repository publication may proceed only after the exact candidate, export, package, CI, history, and commit-identity gates pass |

## Current release qualifications

1. Case J physics closure and the AEDT historical/current outcomes remain truthful documented limitations and must not be cosmetically converted to `PASS`.
2. These outcomes are not publication blockers when evidence integrity, unchanged thresholds, current/historical semantics, known-limitations disclosure, privacy, and proprietary-content gates pass.
