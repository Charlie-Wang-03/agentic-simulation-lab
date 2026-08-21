# Agent operating contract

Agents must treat manifests and result files as sources of truth, never infer a pass from a zero exit alone, and never relax acceptance thresholds merely to obtain a green result. Begin with `list`, `info`, and `doctor`; use `--dry-run` before solver execution. Proprietary solver launches require explicit task authorization and an available license.

Use supported APIs, CLIs, and scripting interfaces first. GUI or computer-use automation is not a default execution path and requires a case-specific justification and authorization. Never alter system or license environment variables, registries, firewalls, installations, or license services to make a run pass. Missing software or licenses are `BLOCKED`, not invitations to bypass controls.

Repository writes are limited to this project. Keep generated data under `artifacts/`; never upload solver inputs or outputs to external services. Preserve `FAIL` and `BLOCKED` evidence and do not destructively delete evidence. Public files use project-relative paths and must not include hostnames, user directories, license-server details, tokens, private addresses, proprietary binaries, solver databases, or copied vendor documentation.

Subprocesses use explicit argument lists, validated executables, bounded timeouts, checked return codes, captured logs, and cleanup. Do not use `shell=True`. Solver executables may come only from documented official installation discovery, trusted local configuration, or explicit user input; reject repository, temporary, network-share, and downloaded arbitrary binaries.

Solver benchmarks run offline after dependencies are installed. Network access is limited to trusted package managers and official documentation lookup; CI contains no solver launches or license secrets. Run the static validation pipeline after edits. Skills under `agent/skills/` provide focused procedures.
