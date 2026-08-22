# Execution security

## Subprocess policy

Public Python code uses argument lists, never `shell=True` or `os.system`. Synchronous subprocess calls have explicit timeouts and checked return codes. Solver stdout/stderr and run records belong under ignored `artifacts/`. A timeout is a durable `FAIL` unless evidence specifically establishes an external license/product block.

`python tools/check_subprocess_policy.py` enforces the static baseline in CI. Long-running `Popen` use must have an explicit deadline, timeout-aware wait, ownership tracking, and cleanup of only the process started by the case.

Process ownership must come from an explicit launcher or solver API process identifier. A process that merely appeared after a baseline snapshot is not owned. If a constructor fails before returning a reliable PID, destructive cleanup is not attempted and the result records `NOT_CONFIRMED` cleanup evidence.

## Executable trust

Solver executables may be selected only through documented official installation discovery, trusted project-local configuration, or an explicit user-provided path. Before launch, adapters must validate that the candidate:

- is an existing local regular executable with the expected product filename;
- is not inside the repository, `.venv`, an artifact directory, a temporary directory, or a network/UNC path;
- has product/version metadata consistent with the intended Ansys product where the platform exposes such metadata;
- matches the requested product and release sufficiently for the adapter;
- is never a binary downloaded by a benchmark.

Failure to establish trust is `BLOCKED`; the agent must not search arbitrary downloads or weaken checks.

## Network and environment boundaries

The project is Local First. Its core runtime requires no hosted model or online AI API and contains no telemetry or automatic upload. Solver benchmarks run offline after dependencies are installed. They do not upload models or results, invoke SaaS APIs, download examples, or fetch binaries. Package installation may use the configured trusted package index; documentation audits may read official Ansys and GitHub pages.

The project may set process-scoped discovery values needed by an official API. It must not persistently alter system environment variables, registries, firewalls, installations, license services, or license-server settings. CI contains no proprietary solver, license secret, or solver launch.
