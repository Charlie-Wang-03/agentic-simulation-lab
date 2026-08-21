# Diagnose solver

## When to use

Use for installation, dependency, launch, API, license, or solver-failure questions.

## Preconditions

Read the manifest requirements. Active probes and proprietary launches require
explicit authorization; static diagnosis does not.

## Main commands

Run `agentic-sim doctor`, then `agentic-sim doctor --probe <solver>` only when
a trusted executable path must be checked. Diagnose in order: Python, package,
executable, product/license, API/session, solver execution, result contract, and
physics validation.

## Evidence source

Current `doctor` output, supported API/version documentation, sanitized local logs,
the manifest result file, and its run record. Discovery is not launch evidence.

## Stop conditions

Stop at the narrowest `FAIL` or `BLOCKED` layer. Missing legal runtime/license is
`BLOCKED`; an executable solver error is `FAIL`. Do not proceed to physics when the
authoritative result is missing or invalid.

## Forbidden shortcuts

Do not alter installations, registries, firewalls, system/license environment,
transport modes, or launch undocumented servers. Do not use GUI automation by
default. Redact usernames, hostnames, private addresses, license endpoints, and
absolute user paths from durable reports.

## Expected output

A staged `PASS`/`FAIL`/`BLOCKED`/`NOT_RUN` ladder, narrowest cause, versions,
supported constructor/API evidence, cleanup status, and owned-process remainder.
