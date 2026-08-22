# Real simulation results and provenance

**English** | [简体中文](SIMULATION_RESULTS.zh-CN.md)

The project uses two deliberately separate visual layers:

- SVGs under `assets/gallery/`, `assets/showcase/`, plus the hero and workflow graphics, are explanatory schematics, status maps, or branding.
- PNGs under `assets/simulations/<domain>/` are paper-style figures deterministically rendered from the adjacent sanitized `*.evidence.json` solver samples.

The PNGs are not GUI screenshots and do not reconstruct values that are absent from the evidence. Each evidence file records the solver, units, validation summary, source hashes, and whether importing that compact evidence required a solver rerun.

## Domain-level result inventory

| Domain | Representative benchmark | Solver-derived evidence represented | Paper-style PNG | New solver rerun needed for this upgrade? |
|---|---|---|---|---|
| Mechanics | [`mechanics/static-cantilever`](../benchmarks/mechanics/cases/smoke_static_cantilever.py) | 621 solved 3-D nodes; displacement magnitude and equivalent stress | [figure](assets/simulations/mechanics/static-cantilever.png) · [evidence](assets/simulations/mechanics/static-cantilever.evidence.json) | No; the branch already contained a qualified fresh Mechanical run import |
| Thermal | [`thermal/thermal-conduction`](../benchmarks/thermal/cases/smoke_thermal_conduction.py) | SOLID70 nodal temperature across the solved solid; transverse extrusion is identified in the figure | [figure](assets/simulations/thermal/thermal-conduction.png) · [evidence](assets/simulations/thermal/thermal-conduction.evidence.json) | No |
| CFD | [`cfd/fluent-cylinder-unsteady`](../benchmarks/cfd/cases/smoke_fluent_cylinder_unsteady.py) | Unsteady Fluent node velocity magnitude and pressure at 120 s | [figure](assets/simulations/cfd/fluent-cylinder-unsteady.png) · [evidence](assets/simulations/cfd/fluent-cylinder-unsteady.evidence.json) | No |
| Multiphysics | [`multiphysics/cht-fluent`](../benchmarks/multiphysics/cases/smoke_cht_fluent.py) | Conformal fluid–solid temperature and velocity fields | [figure](assets/simulations/multiphysics/cht-fluent.png) · [evidence](assets/simulations/multiphysics/cht-fluent.evidence.json) | No |
| Materials | [`materials/plasticity`](../benchmarks/materials/cases/smoke_plasticity.py) | SOLID185 bilinear plasticity load–unload response | [figure](assets/simulations/materials/plasticity.png) · [evidence](assets/simulations/materials/plasticity.evidence.json) | No |
| Electromagnetics | [`electromagnetics/magnetostatic`](../benchmarks/electromagnetics/cases/smoke_magnetostatic.py) | Maxwell 2-D radial `Mag_B` samples; revolved only by the solved axisymmetry | [figure](assets/simulations/electromagnetics/magnetostatic.png) · [evidence](assets/simulations/electromagnetics/magnetostatic.evidence.json) | No |
| Acoustics | [`acoustics/acoustic-cavity-modal`](../benchmarks/acoustics/cases/smoke_acoustic_cavity_modal.py) | FLUID30 pressure eigenvector on three orthogonal mid-planes | [figure](assets/simulations/acoustics/acoustic-cavity-modal.png) · [evidence](assets/simulations/acoustics/acoustic-cavity-modal.evidence.json) | No |
| Porous / geomechanics | [`porous_geomechanics/terzaghi-consolidation`](../benchmarks/porous_geomechanics/cases/smoke_terzaghi_consolidation.py) | CPT212 pore-pressure and displacement snapshots | [figure](assets/simulations/porous_geomechanics/terzaghi-consolidation.png) · [evidence](assets/simulations/porous_geomechanics/terzaghi-consolidation.evidence.json) | No |
| DEM | [`dem/angle-of-repose`](../benchmarks/dem/cases/smoke_angle_of_repose.py) | Final Rocky 3-D particle positions, sizes, and speeds | [figure](assets/simulations/dem/angle-of-repose.png) · [evidence](assets/simulations/dem/angle-of-repose.evidence.json) | No |
| SPH | [`sph/sph-dam-break`](../benchmarks/sph/cases/smoke_sph_dam_break.py) | Rocky Lagrangian particle position and speed at three solver times | [figure](assets/simulations/sph/sph-dam-break.png) · [evidence](assets/simulations/sph/sph-dam-break.evidence.json) | No |
| Phase / reactive | [`phase_reactive/fluent-melting`](../benchmarks/phase_reactive/cases/smoke_fluent_melting.py) | Fluent enthalpy–porosity liquid-fraction snapshots | [figure](assets/simulations/phase_reactive/fluent-melting.png) · [evidence](assets/simulations/phase_reactive/fluent-melting.evidence.json) | No |

All 11 representatives now have a report-style PNG. The compact evidence was sufficient, so this upgrade launched no proprietary solver. The existing SVG renders beside the evidence remain useful lightweight vector summaries, but the PNGs are the canonical public result figures.

## Rebuild and verify

Install the `visuals` extra (or the development environment), then run:

```bash
python tools/build_simulation_visuals.py
python tools/build_simulation_visuals.py --check
```

The freshness check verifies the SVG content and each PNG's dimensions, render-version marker, and source-evidence SHA-256. See the [development guide](DEVELOPMENT.md) for the explicit, maintainer-only local import workflow.
