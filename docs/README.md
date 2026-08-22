# Documentation

**English** | [简体中文](README.zh-CN.md)

Agentic Simulation Lab turns physical intent into reproducible, Agent-orchestrated simulation workflows with explicit physics checks. Choose the route that matches what you want to do, then follow links into focused technical material.

## Start here

| I want to… | Read next | Outcome |
|---|---|---|
| understand the project in five minutes | [Agent-first workflow](tutorials/agent-first-workflow.md) | See what the Agent controls, what the solver computes, and how evidence determines status |
| install and inspect the lab | [Quick Start](tutorials/quickstart.md) | Install the core package, browse cases, diagnose integrations, and dry-run safely |
| learn simulation automation step by step | [Flagship learning path](LEARNING_PATH.md) | Progress from a cantilever to thermal, CFD, multiphysics, acoustics, DEM, and datasets |
| inspect authentic result figures and provenance | [Real simulation results](SIMULATION_RESULTS.md) | Compare one solver-derived paper-style figure for each of the 11 domains |
| browse every public simulation | [Simulation and benchmark catalog](BENCHMARKS.md) | Compare all 134 cases by physics, solver, status, validation basis, code, and visual evidence |
| generate Scientific-AI data | [Dataset tutorial](tutorials/generate-a-dataset.md) | Build, inspect, reload, and validate Dataset Contract v1 output |
| contribute a benchmark or change code | [Development guide](DEVELOPMENT.md) | Follow manifest, result-contract, static-validation, and publication rules |

## Getting started and learning

- [Quick Start](tutorials/quickstart.md) — the shortest solver-free path from installation to `list`, `info`, `doctor`, and `--dry-run`.
- [Project installation](tutorials/install-project.md), [Windows](tutorials/install-windows.md), and [macOS](tutorials/install-macos.md) — platform-specific setup.
- [Run a benchmark](tutorials/run-a-benchmark.md) — authorized Mechanical execution and evidence review.
- [Flagship learning path](LEARNING_PATH.md) — eight curated cases with physics, automation lessons, requirements, and cost.
- [Ansys Student](tutorials/install-ansys-student.md) and [AEDT Student](tutorials/install-aedt-student.md) — product-specific installation notes and limits.

## Simulations and visual evidence

- [Complete benchmark catalog](BENCHMARKS.md) — generated from manifests, source docstrings, and compact evidence.
- [Real simulation results and provenance](SIMULATION_RESULTS.md) — 11 report-style PNGs, their benchmark sources, evidence representation, and rerun status.
- [Project metrics](PROJECT_METRICS.md) — generated domain, status, role, and solver-label counts.
- [Solver support matrix](SOLVER_MATRIX.md) — historical tested evidence versus current environment diagnosis.
- [Known limitations](known-limitations.md) — preserved failures, external blocks, and migration qualifications.
- [Domain implementations](../benchmarks/) and [detailed reports](reports/).

The gallery separates explanatory SVG domain maps from genuine solver-derived PNG result figures. Cases without a true result figure receive no decorative result placeholder. Manifests and referenced result files remain the status sources of truth.

## Concepts and technical reference

- [Architecture](ARCHITECTURE.md) — registry, lazy integrations, subprocess execution, artifact routing, and result contracts.
- [Validation policy](VALIDATION.md) — exact `PASS`, `FAIL`, `BLOCKED`, `PARTIAL`, and `NOT_RUN` meanings.
- [Datasets](DATASETS.md) — Case Result Contract v1 versus Dataset Contract v1, portability, and Python loading.
- [Execution security](EXECUTION_SECURITY.md) — subprocess, executable-trust, network, and environment boundaries.
- [Tested environments](TESTED_ENVIRONMENTS.md) — historical environment evidence and platform scope.

## Project, safety, and maintainer material

- [Development](DEVELOPMENT.md), [contributing](../CONTRIBUTING.md), and [Agent workflow](../agent/WORKFLOW.md).
- [Ansys usage and compliance](ANSYS_USAGE_AND_COMPLIANCE.md), [Student product limits](STUDENT_PRODUCT_LIMITS.md), and [disclaimer](../DISCLAIMER.md).
- [Security policy](../SECURITY.md) and [support](../SUPPORT.md).
- [`release/`](release/) — source audits, traceability, decisions, regression records, and checklists for maintainers; not prerequisite reading for newcomers.

## Bilingual documentation policy

Newcomer-facing core material is bilingual by default: the root README, documentation home, Quick Start and installation guides, flagship learning path, benchmark/gallery introduction, dataset tutorial, and other high-value user tutorials. Each translated pair links directly to its counterpart.

Low-level architecture, generated metrics, implementation internals, security detail, compliance source audits, reports, and release/maintainer records may remain English-only. This keeps important entry points accessible without creating translations likely to drift from technical truth. Chinese pages are edited as natural technical writing rather than literal sentence-by-sentence copies.

```bash
python tools/build_catalog.py
python tools/build_project_metrics.py
python tools/build_gallery.py
```

Use each command's `--check` option in validation. Do not hand-edit generated catalog tables or convert a successful process exit into physics `PASS`.
