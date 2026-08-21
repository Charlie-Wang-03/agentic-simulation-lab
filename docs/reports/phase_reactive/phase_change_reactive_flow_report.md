# Phase Change / Reactive Flow Report

Generated: 2026-08-20

## Outcome

The suite executed the available native Ansys models and physically grounded reduced-order benchmarks. PASS requires the case-specific physics and conservation checks, not merely a solver exit. Cases G and J remain FAIL: G did not establish a credible internal premixed flame, and J did not close transient reactive-CHT conservation under the available post-processing estimate.

| Case | Model / solver | Status | Main evidence |
|---|---|---:|---|
| A | One-phase Stefan semi-analytic benchmark | PASS | interface/energy error max 7.642e-05 |
| B | Fluent enthalpy-porosity melting | PASS | final liquid fraction 0.2232; sparse energy error 0.1542 |
| C | Fluent phase change + Boussinesq buoyancy | PASS | buoyant front std 0.0006321 m |
| D | Reduced-order moving heat source + latent fraction | PASS | power/speed melt-pool trends checked |
| E | Numerical plug reaction-diffusion vs analytic first order | PASS | max profile error 0.003196 |
| F | Fluent species transport + finite-rate CH4/air | PASS | conversion 0.1278; carbon/energy errors 4.735e-06/0.01622 |
| G | Fluent premixed finite-rate autoignition | FAIL | two targeted retests exhausted; final Tmax 3263.6 K and carbon error 0.2669 |
| H | Fluent split fuel/oxidizer diffusion reaction | PASS | Tmax 1031 K; hot/reaction overlap 0.7787 |
| I | Fluent finite-rate combustion + P-1 | PASS | delta Tmax -468.4 K; coarse energy error 0.2492 |
| J | Fluent reacting fluid + solid CHT | FAIL | corrected total-enthalpy balance error 0.1595 versus unchanged 0.10 limit |
| K | Phase-change parametric dataset (reduced-order Stefan) | PASS | 12 cases |
| L | Reactive-flow parametric dataset (reduced-order chemistry) | PASS | 12 cases |

## Solver and model inventory

- MAPDL 2026 R1 / 261: a real transient PLANE55 probe accepted temperature-dependent conductivity, heat capacity, density, and ENTH tables. This confirms the script path for enthalpy/latent-heat thermal analysis; Case A itself is the independent Stefan reference.
- Fluent Student 2026 R1 / 261: native Solidification & Melting (enthalpy-porosity), laminar flow, Boussinesq buoyancy, Species Transport, one-step methane-air volumetric finite-rate reactions, P-1 radiation, and conformal fluid-solid CHT were executed.
- Chemistry: Fluent built-in `methane-air` one-step mechanism with named species CH4, O2, CO2, H2O, N2. No detailed mechanism or imposed artificial temperature field was used.
- Reduced-order scope: D, E, K and L are explicitly identified as physically grounded numerical/analytic models, not Fluent results. K/L validate reusable dataset organization; they do not claim native-solver ensemble provenance.

## Phase-change results

Case A used rho/cp/k/latent properties and recovered the Stefan interface with maximum energy relative error 7.642e-05. Case B used 800 cells, dt=30.0 s, and 180000.0 J/kg latent heat. Its 30-3600 s sparse wall-flux integral is 3.831e+04 J/m versus 3.24e+04 J/m reconstructed enthalpy gain (15.4% smoke-level difference).
Case C compared zero gravity and buoyancy on the same PCM cavity. Final average liquid fractions were 0.08516 and 0.09026; the buoyant front became non-planar and velocity nonzero.

## Reaction and combustion results

Case E matched first-order plug-flow conversion with maximum absolute error 0.003196. Case F produced a native reaction-rate field, 0.1278 conversion, Tmax 1029 K, species-sum error 9e-11, carbon error 4.735e-06, and total-enthalpy/wall-heat closure error 0.01622.
Case G exhausted its two permitted targeted retests without changing acceptance thresholds. The first lower-enthalpy, internally ignited run held Tmax to 2784.062 K and carbon error to 0.00013736, but its reaction peak remained upstream at x=0.003 m. Raising inlet velocity to 0.25 m/s moved the peak only to the strict x=0.004 m boundary and introduced temperature clipping/reverse flow: Tmax=3263.591 K and carbon error=0.266863. The final status is FAIL. The evidence supports native finite-rate combustion, not a validated premixed flame or flame-speed result.
Case H passed a weak diffusion-flame/reaction-layer test. At the reaction peak both CH4 and O2 were present; strong-reaction/hot-region overlap was 0.7787. The modest temperature rise is reported without claiming an engineering-strength flame.
Case I used equal 100-step branches from the same reacting initial state. P-1 with absorption coefficient 20 1/m changed Tmax by -468.4 K and mean temperature by -23.17 K. Its instantaneous coarse-transient total-enthalpy/wall-heat balance error was 0.2492 with 0.01351 mass-flow imbalance; the 30% energy tolerance is explicitly smoke-level. The inherited G failure remains explicit.
Case J created native reacting-fluid/solid zones and coupled interfaces, with nonzero reaction and wall heat transfer. The corrected 600-step retest compared inlet/outlet total-enthalpy flux with integrated outer-wall heat and measured final-step transient enthalpy accumulation. Carbon error was 2.12e-08, mass-flow error was 1.93e-08, and seven checks passed. The global total-enthalpy balance error was 0.1595 against the unchanged 0.10 limit, so J remains FAIL.

## Dataset and validation

Case K and L each contain 12 parameter cases with coordinates, connectivity, physical fields, units, solver/model provenance, and named chemistry metadata; K additionally uses unified time samples. Reload validation status: PASS. Checks include finite values, phase fraction bounds/trends, Stefan energy balance, species bounds and sum, reaction-rate finiteness, heat-release/temperature consistency, time ordering, and metadata completeness.

## Student-license evidence

Observed edition: Ansys Student 2026 R1. Ansys currently lists 128K structural nodes/elements and 1 million fluid cells/nodes, with up to four CPU cores. This suite exercised at most 900 Fluent cells and observed no combustion, reaction, melting, radiation, or CHT feature denial. The numerical ceilings were not deliberately exhausted. Official source: <https://www.ansys.com/en-gb/home/academic/students/ansys-student>.

## Capability matrix

| Capability | Result | Evidence / qualification |
|---|---:|---|
| latent heat | PASS | A analytic balance; MAPDL ENTH probe; B native Fluent |
| melting / solidification | PASS | B transient native model |
| enthalpy-porosity | PASS | B native liquid-fraction field |
| buoyancy-driven melting | PASS | C front deformation and nonzero flow |
| moving heat source | PASS | D reduced-order trend benchmark |
| reaction-diffusion | PASS | E analytic profile comparison |
| species transport | PASS | F/H native named species fields |
| finite-rate chemistry | PASS | F native volumetric reaction-rate field |
| premixed combustion | FAIL | G burns but internal flame sanity fails |
| diffusion flame | PASS | H mixing/reaction-zone overlap; weak flame qualification |
| combustion radiation | PASS | I P-1 fields and controlled temperature response; inherits G caveat |
| reactive CHT | FAIL | J native coupling executes; conservation criterion fails |
| phase-change dataset | PASS | K + reload validator; reduced-order provenance |
| reactive-flow dataset | PASS | L + reload validator; reduced-order provenance |

## Advanced directions (not executed in this round)

Detailed chemistry; stiff chemistry integration; turbulent combustion; flamelet models; partially premixed combustion; ignition/extinction; pollutant formation; spray combustion; evaporation; boiling; cavitation; condensation; pyrolysis; battery thermal runaway; reacting porous media.

## Reproducibility

Discover cases with `agentic-sim list --domain phase_reactive`; dry-run a suite with `agentic-sim run phase_reactive --suite --dry-run`. New outputs belong under `artifacts/runs/`; the ignored local legacy evidence is under `artifacts/legacy/`.
