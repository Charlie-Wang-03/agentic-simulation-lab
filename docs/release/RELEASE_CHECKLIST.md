# Release checklist

Checked: 2026-08-21

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
- [ ] Final static, clean-package, package-content, and exact-revision A/B export checks pass after hardening

## Maintainer decisions and publication actions

- [x] Maintainer selected Apache-2.0; exact license text and package metadata implemented
- [x] Public citation identity limited to `Charlie-Wang-03`; CFF 1.2.0 schema validation passed
- [ ] Create public GitHub repository
- [ ] Enable private vulnerability reporting if desired
- [ ] Configure repository description/topics
- [ ] Review first commit
- [ ] Publish first release

Unchecked publication items remain evidence-driven. The maintainer authorized private `main` publication-preparation commits and, after all hard gates pass, creation of one independent public repository with a single clean initial commit. Tagging, GitHub release publication, PyPI, and Zenodo remain unauthorized.
