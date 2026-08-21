# Official-source audit

Checked: 2026-08-21

Status: **PASS for documented guidance and the approved Apache-2.0 boundary.**

This is an engineering compliance review, not legal advice. Only Ansys and GitHub primary sources were used. The installed product clickwrap and the maintainer's legal review remain authoritative for actual use.

## Conclusions

- Agentic Simulation Lab is an independent, script-driven validation project. It is not an Ansys product, is not endorsed or certified by Ansys, and does not use Ansys logos or trade dress.
- Current trademark guidance tells third parties not to use Ansys marks in product names. The public identity, Python distribution/package, CLI, URLs, and documentation therefore use the neutral Agentic Simulation Lab identity. Ansys product names remain referential interoperability terms only.
- Here, *benchmark* means a canonical physics validation case against an analytical, conservation, or documented numerical reference. It does **not** mean competitive product analysis or comparison.
- Free Ansys Student downloads are limited by current academic terms to student instruction, student projects, and student demonstrations. Research, Associate, Teaching, and other academic categories have distinct permissions and conditions. Academic programs exclude commercial activity and competitive analysis. Users must follow the category actually granted to them.
- The Apache-2.0 repository license and an Ansys product license are independent. Apache-2.0 covers only original repository content; it does not license Ansys software, documentation, examples, trademarks, or generated proprietary project files.
- Current Ansys Student desktop guidance is Windows-focused. Core Python installation, manifests, catalog inspection, static validation, and dry-runs are designed for Windows and macOS. Local Student solver execution on macOS is not claimed.
- PyAnsys clients can be cross-platform even when a local solver is unavailable. For example, current PyMAPDL documentation supports its Python package on Windows, macOS, and Linux but states that MAPDL itself is not macOS-compatible; a licensed remote or containerized solver is a separate arrangement.
- GitHub identifies LICENSE as a distinct community-health item and states that an open-source license enables others to use, change, and distribute a project. The maintainer approved Apache-2.0 and the exact reviewed text is present at the repository root.
- GitHub private vulnerability reporting is a repository setting that can only be enabled after publication by an owner or administrator. `SECURITY.md` therefore directs reporters to that channel without inventing an email address.

## Repository-content review

The candidate public tree was reviewed for copied vendor examples, proprietary solver files, generated databases, executables, local license data, and private host paths.

- No Ansys executable, library, installer, license file, case/database file, or vendor documentation copy is intended for publication.
- No file identifies itself as a copied Ansys official example. The HFSS WR-90 case was compared with the cited official inductive-iris example: both necessarily use public PyAEDT waveguide/port/setup APIs, but the repository case has different geometry, dimensions, sweep, validation target, control flow, and prose. No example narrative, filter parameter set, downloaded asset, notebook, or source block is redistributed. Other benchmark implementations are repository-authored scripts using public APIs and locally generated meshes or small original geometry assets.
- Generated solver outputs and legacy evidence stay under ignored `artifacts/` paths.
- `THIRD_PARTY_NOTICES.md` must list only third-party material actually shipped; dependencies alone are not vendored content.
- `docs/release/SOURCE_PROVENANCE.md` classifies shipped content and pins every allowed non-text fixture by SHA-256.
- The automated public-tree, privacy, and source-provenance audits are the final machine-enforced evidence. A failure in any audit overrides this narrative result.

## Ansys primary sources

1. [Download Ansys Student](https://www.ansys.com/en-gb/home/academic/students/ansys-student) — current Windows platform guidance, included products, problem-size limits, hardware requirements, and license duration.
2. [Ansys academic usage terms](https://www.ansys.com/legal/terms-and-conditions/academic-usage) and [current General Terms/Product Codes index](https://www.ansys.com/legal/agtc) — current category distinctions, non-proprietary-use conditions, and restrictions on commercial activity and competitive analysis.
3. [Ansys Trademark Usage Guidelines](https://www.ansys.com/content/dam/legal/ansys-trademark-usage-guidelines.pdf) — referential word-mark use, first-use marking, acknowledgement, no implied affiliation, no logo use without permission, and no Ansys mark in a third-party product name.
4. [Ansys 2026 R1 Installation Guides](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/pdf/ANSYS_Inc._Installation_Guides.pdf) — current supported Windows platform details and proprietary-document notice.
5. [HFSS Student limitations](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Content/GettingStarted/HFSSStudentLimitations.htm) — official evidence that AEDT Student capabilities are subject to product-specific limits.
6. [Install PyMAPDL](https://mapdl.docs.pyansys.com/version/stable/getting_started/install_pymapdl.html) and [PyMAPDL and macOS](https://mapdl.docs.pyansys.com/version/stable/getting_started/macos.html) — cross-platform Python client support, licensed-solver requirement, and the local macOS limitation.
7. [PyRocky getting started](https://rocky.docs.pyansys.com/version/stable/getting_started/index.html) — official package installation and licensed Rocky requirement.
8. [PyAEDT inductive iris waveguide filter](https://examples.aedt.docs.pyansys.com/version/dev/examples/high_frequency/radiofrequency_mmwave/iris_filter.html) — API-concept comparison used for the copied-example audit; no source or assets are redistributed.

## GitHub primary sources

1. [Adding a license to a repository](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/adding-a-license-to-a-repository) — effect and placement of a detectable repository license.
2. [About community profiles for public repositories](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories) — README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, security policy, and issue-template expectations.
3. [Adding a security policy](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/add-security-policy) — repository instructions for vulnerability reports.
4. [Configuring private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) — owner/admin-only post-publication configuration.
5. [Use `GITHUB_TOKEN` for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token) — least-privilege workflow permissions.

## Release implications

- Technical and documentation work may proceed.
- Case G remains a frozen physics `FAIL`; it must not be re-run or reclassified for release optics.
- Solver regression artifacts must remain ignored and must never contain license-server details.
- The final release audit must verify the exact Apache-2.0 text, SPDX metadata, package inclusion, and separation from Ansys product licensing.
- Truthful documented solver `FAIL`, `BLOCKED`, and `NOT_RUN` outcomes are release qualifications, not publication blockers; missing, inconsistent, misleading, or undisclosed evidence remains a blocking audit failure.
