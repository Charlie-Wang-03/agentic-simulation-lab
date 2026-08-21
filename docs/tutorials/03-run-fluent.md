# Tutorial 3: run a Fluent benchmark

Install the Fluent extra, inspect `cfd/fluent-laminar-channel`, and verify that no other Fluent session owns the intended resources. Execute through the CLI. The benchmark builds a mesh, solves the flow, exports fields, and compares the velocity profile and pressure drop against analytical expectations. Preserve the generated run record when reporting regressions.
