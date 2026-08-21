# Repository license decision

Status: **APPROVED AND IMPLEMENTED**

The maintainer explicitly approved **Apache License 2.0** (`Apache-2.0`) on 2026-08-21. The root `LICENSE`, project metadata, documentation, contribution terms, and package inclusion now implement that decision.

This decision covers only original repository code and documentation. It cannot grant rights to Ansys software, documentation, examples, trademarks, or proprietary output formats.

## Apache-2.0 implementation

The reviewed implementation is:

- the exact, unmodified Apache License 2.0 text from `https://www.apache.org/licenses/LICENSE-2.0.txt` is the root `LICENSE`;
- `project.license = "Apache-2.0"` and `project.license-files = ["LICENSE"]` are declared in `pyproject.toml` using the declared `setuptools>=77` build backend;
- repository documentation and package metadata state `Apache-2.0`;
- wheel and sdist must include `LICENSE` and are checked before publication;
- use `Charlie-Wang-03` only as the public project/maintainer identity, without inventing a legal name or email.

No upstream NOTICE attribution requiring preservation was found in the tracked candidate. Dependencies are installed separately and no third-party source is vendored, so a project `NOTICE` file would be inaccurate and must not be created merely for formality. Reassess this if vendored content is ever added.

Apache-2.0 licenses only repository-owned content. It does not license Ansys software, documentation, examples, trademarks, proprietary solver formats, or unrelated third-party dependencies.

## Verification rule

The release audit hashes `LICENSE` against the reviewed unmodified text and checks the SPDX/package declarations. Package, public-tree, provenance, and exact-revision clean-export audits must all pass. Any later license-text or metadata change requires a new maintainer review.
