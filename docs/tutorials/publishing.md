# Publishing checklist

Publication is a maintainer-controlled phase, not an agent default.

## Freeze and export the candidate

Never change the private R&D mother repository to public. Freeze an exact commit,
then create a clean, history-free candidate under ignored artifacts:

```text
python tools/export_public.py --revision <exact-private-main-sha> --output artifacts/public-exports/export-a
python tools/export_public.py --revision <exact-private-main-sha> --output artifacts/public-exports/export-b
```

The tool reads tracked content from the resolved Git commit rather than copying the
working tree. Its small policy includes public project/code/documentation paths,
excludes artifacts and local configuration, rejects unknown top-level paths and
proprietary/generated extensions, refuses a non-empty destination, and writes a
local report outside the export. It audits the exported directory itself with:

```text
python tools/check_public_tree.py --root artifacts/public-exports/export-a
python tools/check_source_provenance.py --root artifacts/public-exports/export-a
python tools/check_public_tree.py --root artifacts/public-exports/export-b
python tools/check_source_provenance.py --root artifacts/public-exports/export-b
```

For the same commit and policy, compare both reports' sorted file lists, per-file
SHA-256 values, and tree SHA-256. They must be identical. Each export contains no
`.git`, private branch/history, remote, artifacts, local config, or private path.
The public repository must be created independently and only after manual review.

1. Review `docs/release/OFFICIAL_SOURCE_AUDIT.md` and current Ansys terms.
2. Verify the approved Apache-2.0 `LICENSE`, SPDX/package metadata, and its separation from the Ansys product license.
3. Run the full static, package, privacy, link, tutorial-pair, and release audits.
4. Confirm generated artifacts, `.venv`, secrets, solver databases, and private identity data are ignored.
5. Review `git status --short` and `git status --ignored`; stage files deliberately, never with an unreviewed bulk action.
6. After explicit publication authorization and successful hard gates, use one reviewed clean export in a new empty directory; do not clone the private repository or copy `.git`.
7. In that new directory only, run `git init`, create branch `main`, make one clean initial commit, create the empty public repository `Charlie-Wang-03/agentic-simulation-lab`, and push only `main`.
8. Configure the metadata draft and security settings, then review the v0.1.0 release plan before any tag or publication.

The public repository has independent history: no private remote, branch, commit, tag, reflog, worktree metadata, or R&D-only file may cross this boundary.

Only `Charlie-Wang-03` is an allowed public maintainer identifier. Use only maintainer-supplied sanitized Git metadata; never guess or publish a personal name, private email, host, or license endpoint.
