# Ansys usage and compliance

Checked: 2026-08-21

Agentic Simulation Lab is an independent project. It is not affiliated with, endorsed by, certified by, or supported by Ansys, Inc. Ansys and its product names are used only to identify interoperability targets, never as this project’s product identity. No Ansys logo or trade dress is used.

## Two separate licenses

1. The **Apache-2.0 repository license** governs only original source code, documentation, and original small fixtures in this repository.
2. An **Ansys product license** governs the user's separately obtained Ansys software. It is never supplied, extended, bypassed, or replaced by this repository.

Neither license grants rights under the other. Repository publication cannot redistribute Ansys executables, libraries, installers, documentation, official examples, license files, or proprietary project/database formats.

## License categories are not interchangeable

Current official academic terms distinguish free Student downloads and Teaching/EduPack programs from Research and Associate programs. Free Student downloads are limited to student instruction, student projects, and student demonstrations. Research and Associate categories have different non-proprietary research permissions and institutional conditions. Academic programs exclude commercial activity and competitive analysis. No user should assume that a Student license authorizes all academic research or that an open-source repository license expands any Ansys license.

Solver execution requires separately obtained Ansys software and a license appropriate for the intended use. Users are responsible for the installed clickwrap, order/license form, current academic terms, export rules, and product-specific limits that apply to them.

In this project, *benchmark* means a canonical physics validation case: compare a solver result with an analytical solution, conservation law, dimensional relationship, reload invariant, or documented physical trend. It never means comparing Ansys against another commercial product or ranking vendors.

## Safe execution boundaries

- Obtain Ansys software and licenses only through authorized official or institutional channels.
- Never change license servers, registry state, installations, security controls, or system environment merely to run a case.
- Treat missing software, packages, license capacity, or Student-edition capability as `BLOCKED`.
- Run only after `list`, `info`, `doctor`, validation, and `--dry-run`.
- Keep generated files under ignored `artifacts/`; do not publish proprietary solver databases.
- Solver benchmarks are offline and do not upload inputs or outputs.

See the [official-source audit](release/OFFICIAL_SOURCE_AUDIT.md), [Student product limits](STUDENT_PRODUCT_LIMITS.md), and [repository license decision](release/LICENSE_DECISION.md).
