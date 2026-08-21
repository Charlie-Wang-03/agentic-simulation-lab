# SPH vs Fluent VOF comparison

Status: **PASS**

The two real Ansys solutions use exactly similar 1:10 geometry. Front propagation is compared with gravity-scaled time and tank-normalized distance; pointwise agreement is not required.

Dimensionless front RMSE: `0.21548286015934381`
SPH mass drift: `0.0`
VOF volume-fraction drift: `0.06818732828245491`

Raw SPH pressure/free-surface fields and Fluent pressure/volume-fraction snapshots are retained. The archived Fluent result has no matching wall-pressure probe or solver-runtime record, so this report does not claim numerical wall-pressure or runtime agreement.

## Checks

- sph_pass: True
- vof_pass: True
- five_comparison_points: True
- dimensionless_front_rmse_lt_0p25: True
- sph_mass_drift_lt_1pct: True
- vof_volume_drift_lt_8pct: True
