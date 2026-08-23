# Ansys usage and compliance

Checked: 2026-08-22

Agentic Simulation Lab is an independent project. It is not affiliated with, endorsed by, certified by, or supported by Ansys, Inc. Ansys and its product names are used only to identify interoperability targets, never as this project’s product identity. No Ansys logo or trade dress is used.

## Two separate licenses

1. The **Apache-2.0 repository license** applies only to rights held by project contributors in their original contributions.
2. An **Ansys product license** governs the user's separately obtained Ansys software. It is never supplied, extended, bypassed, or replaced by this repository.

Neither license grants rights under the other. Apache-2.0 grants no rights in Ansys software, documentation, trademarks, official/vendor assets, or other third-party materials. Solver-derived numerical evidence and project-rendered figures are published as project validation evidence; no underlying Ansys or third-party rights are granted by this repository.

## License categories are not interchangeable

Current official academic terms distinguish free Student downloads from Teaching, Research, Associate, and other Academic programs. Free Student downloads have narrower boundaries around student learning, instruction, student projects, and demonstrations; the other Academic license types have different permissions and conditions. “Academic” or “non-commercial” alone does not establish that a particular use is permitted. No user should assume that a Student license authorizes all academic research or that an open-source repository license expands any Ansys license.

Solver execution requires separately obtained Ansys software and a license appropriate for the intended use. Actual rights depend on the License Type granted to the user, the applicable Agreement, Product Codes, order or clickwrap, and the then-current relevant terms. This repository cannot determine a user's specific authorization. Users are responsible for the terms, export rules, and product-specific limits that apply to them.

In this project, *benchmark* means a canonical physics validation case: compare a solver result with an analytical solution, conservation law, dimensional relationship, reload invariant, or documented physical trend. It never means comparing Ansys against another commercial product or ranking vendors.

Technical provenance, legal/evidence status, and maintainer publication decisions are separate. The 11 frozen historical corpora remain `LEGAL_REVIEW_REQUIRED`; the maintainer separately approved their sanitized evidence with accepted residual legal risk after reasonable diligence found no confirmed redistribution violation. This is not `CLEARED` and does not state or imply Ansys approval.

Future Ansys runs primarily for academic research, research-paper experiments, research datasets, or authoritative paper figures/results require a fresh, purpose-specific licensing and publication decision. They do not inherit the historical approval.

## Safe execution boundaries

- Obtain Ansys software and licenses only through authorized official or institutional channels.
- Never change license servers, registry state, installations, security controls, or system environment merely to run a case.
- Treat missing software, packages, license capacity, or Student-edition capability as `BLOCKED`.
- Run only after `list`, `info`, `doctor`, validation, and `--dry-run`.
- Keep generated files under ignored `artifacts/`; do not publish proprietary solver databases.
- Solver benchmarks are offline and do not upload inputs or outputs.

See the [official-source audit](release/OFFICIAL_SOURCE_AUDIT.md), [Student product limits](STUDENT_PRODUCT_LIMITS.md), and [repository license decision](release/LICENSE_DECISION.md).
