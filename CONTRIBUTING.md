# Contributing

Open a focused issue or pull request. Repository-owned content is licensed under Apache-2.0.

The inbound model is the normal same-license model: contributors retain copyright and intentionally submitted contributions are licensed under Apache-2.0. This project does not require a CLA, DCO sign-off, real name, or private contact information.

Contributions must:

- keep solver integrations optional, lazy, API-first, and vendor-neutral at the agent layer;
- put all generated files under `artifacts/` and never include proprietary solver files, license information, private paths, hostnames, tokens, confidential models, or personal data;
- use normalized statuses and preserve `FAIL`, `BLOCKED`, and `NOT_RUN` evidence;
- define units, provenance, and physical acceptance checks for each new benchmark;
- add a manifest entry and rebuild `benchmarks/catalog.json`;
- keep small public datasets platform-independent and project-relative;
- add or update English and Simplified Chinese user tutorials together;
- use argument-list subprocesses with timeouts and no `shell=True`;
- avoid network access during benchmark execution.

Before submitting, run the static commands in `docs/DEVELOPMENT.md`, including tests, Ruff, catalog/reference checks, link checks, tutorial pairing, and the public-tree/privacy audit. New `PASS` claims require executable evidence and numerical physics checks; a zero exit code is insufficient. By participating, follow the code of conduct.
