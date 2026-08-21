# Known limitations

- Proprietary solvers, licenses, and product modes are not included.
- Historical suite evidence can differ on other releases, hardware, meshes, or numerical settings.
- Premixed-combustion Case G remains `FAIL`: the one-step methane-air model produced an inlet-adjacent reaction peak; a faster-flow diagnostic additionally showed temperature clipping, reverse flow, and carbon imbalance.
- Reactive-CHT Case J remains `FAIL`. The historical final-step result of 15.951% is preserved; a fresh predeclared 10-step accounting window measured 15.842% (and 15.998% for its final step) against the unchanged 10% limit. This rejects final-step sampling noise as the explanation and retains a truthful under-resolved transient balance at the current settings.
- The catalog preserves the AEDT Student electrostatic regression's historical `FAIL`. Fresh staged diagnosis passes Python/PyAEDT, installation discovery, and executable trust, then stops `BLOCKED` at version compatibility: AEDT Student 2025 R2 does not support the default secure-local PyAEDT transport. The task-prohibited insecure/pre-service-pack fallback was not attempted; no session or solver was launched and cleanup found no owned process.
- Electromagnetic transient, Rocky two-way coupling, and selected SPH modes retain explicit `BLOCKED` states tied to documented edition/API limits.
- Several legacy cases are `NOT_RUN` because no unambiguous suite evidence could be attributed during migration.

## Catalog release qualifications

These outcomes are intentionally published as limitations. They do not become `PASS` during release preparation. Publication is blocked only if the evidence is missing or inconsistent, a declared threshold is weakened, the current/historical meaning is misleading, the limitation is undisclosed, or privacy/proprietary-content gates fail.

| Domain/case | Truthful catalog status | Public evidence or qualification |
|---|---|---|
| `electromagnetics/electrostatic` | `FAIL` | Historical release regression remains `FAIL`; current supported-transport compatibility diagnosis is separately `BLOCKED`. |
| `multiphysics/fsi-turek-hron` | `FAIL` | `benchmarks/multiphysics/references/historical_results.json` |
| `phase_reactive/premixed-combustion` | `FAIL` | `benchmarks/phase_reactive/references/targeted_diagnostics.json` |
| `phase_reactive/reactive-cht` | `FAIL` | Fixed-window energy error remains 15.842% against the unchanged 10% threshold. |
| `dem/cfd-dem-two-way` | `BLOCKED` | `benchmarks/dem/references/suite_summary.json` |
| `electromagnetics/transient-magnetic` | `BLOCKED` | `benchmarks/electromagnetics/references/suite_summary.json` |
| `sph/sph-flexible-structure` | `BLOCKED` | `benchmarks/sph/references/suite_summary.json` |
| `sph/sph-non-newtonian` | `BLOCKED` | `benchmarks/sph/references/suite_summary.json` |
| `mechanics/connect` | `NOT_RUN` | No attributable execution evidence; the absence is the declared status. |
| `mechanics/spaceclaim-multibody-geometry` | `NOT_RUN` | No attributable execution evidence; the absence is the declared status. |
| `mechanics/spaceclaim-single-link-geometry` | `NOT_RUN` | No attributable execution evidence; the absence is the declared status. |
