# Release checklist

Checked: 2026-08-22

## Local technical finalization

- [x] Manifest-driven package and CLI exist
- [x] Official-source audit recorded
- [x] Public-tree and privacy scanners implemented
- [x] Source-provenance classifications and hash-pinned binary fixture gate implemented
- [x] Cross-platform static CI configured
- [x] Community files and bilingual installation guidance prepared
- [x] Case J historical 15.951% `FAIL` preserved; fresh 10-step window also retained `FAIL` at 15.842% versus the unchanged 10% limit
- [x] Representative solver regressions completed in the project environment (four `PASS`, AEDT `FAIL`)
- [x] Neutral public distribution/package/CLI identity applied without renaming the private mother repository
- [x] Final static, clean-package, package-content, and exact-revision A/B export checks pass after hardening

## Maintainer decisions and publication actions

- [x] Maintainer selected Apache-2.0; exact license text and package metadata implemented
- [x] Public citation identity limited to `Charlie-Wang-03`; CFF 1.2.0 schema validation passed
- [x] Maintainer accepted the low residual contractual risk for the 11 frozen historical corpora without marking them `CLEARED`
- [x] Create public GitHub repository
- [ ] Enable private vulnerability reporting if desired
- [x] Configure repository description/topics
- [x] Review first commit
- [x] Publish v0.1.0 GitHub Release

Unchecked optional items remain evidence-driven. The maintainer authorized the independent public repository, the annotated `v0.1.0` tag, and the published GitHub Release after all hard gates pass. PyPI and Zenodo publication remain unauthorized and are not part of v0.1.0 finalization.

## Each future public candidate

- [ ] For every solver-derived public evidence set, record generation date, solver/product, actual License Type if known, applicable Agreement, run purpose, source/input provenance, proprietary/vendor asset involvement, publication basis, and publication review status
- [ ] Apply the legal/evidence-status and maintainer-decision matrix; never infer `CLEARED` from a residual-risk approval, technical ownership, or physics `PASS`
- [ ] Treat future academic research, paper experiments, research datasets, and authoritative paper results as a new licensing context; do not inherit this historical decision
- [ ] Confirm the clean export contains no locally referenced official/proprietary assets or solver databases/projects
- [ ] In GitHub Settings, manually verify Private Vulnerability Reporting, Dependabot alerts, Dependabot security updates, secret scanning, push protection, CodeQL/code scanning, and the main-branch ruleset or protection; repository files do not prove these settings
