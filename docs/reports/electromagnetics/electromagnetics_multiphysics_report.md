# Electromagnetics and Multiphysics Report

Generated: 2026-08-16T01:32:28.653609+00:00
Overall status: **PARTIAL** (all supported cases pass; one Student product limitation is BLOCKED)

## Environment and launch

- AEDT: `C:\Program Files\ANSYS Inc\ANSYS Student\v252\AnsysEM\ansysedtsv.exe`; Electronics Desktop Student 2025 R2 (`FileVersion 2025.2.0.1`), live desktop build `2025.2.4`.
- Python `3.12.13` in the local solver environment; PyAEDT `1.4.0`.
- Historical connection diagnostics closed with zero residual processes. Release scripts now expose only the official PyAEDT Student constructor and preserve unsupported launch combinations as `BLOCKED`.
- No manual server prelaunch, session-detection monkey patch, or downgraded transport is permitted. [PyAEDT installation](https://aedt.docs.pyansys.com/version/stable/Getting_started/Installation.html).

## Cases A–H

| Case | Actual solver/model | Principal result | Status |
|---|---|---|---|
| A | Maxwell 2D Electrostatic parallel plates | C=10.4720 pF; mean E=100 V/m; C error=18.27% | PASS |
| B | Maxwell 2D DC Conduction copper bar | R=1.72414e-05 ohm; I=58000 A; P=58000 W | PASS |
| C | Maxwell 2D Magnetostatic coax | L=3.19573e-08 H; B/H mean error=5.99%/5.99% | PASS |
| D | Maxwell 2D AC Magnetic at 1 kHz | skin depth=2.09 mm; Jsurface/Jcenter=2.41; loss positive | PASS |
| E | Maxwell 2D Transient eccentric coax | AEDT: Student does not support Maxwell Transient solution | BLOCKED (Student product limitation) |
| F | HFSS Driven Modal WR-90, 6-12 GHz | TE10 cutoff=6.55714 GHz; cutoff trend validated | PASS |
| G | Maxwell 3D DC Conduction to Icepak `AssignEMLoss` | Source and target solved; mapped temperature exported | PASS |
| H | Maxwell force to Mechanical 261 | Fx=0.020040917 N; deformation=5.91758e-11 m; theory error=18.11% | PASS |

Maxwell 2D capacitance was scaled from per-metre depth to 0.1 m physical depth, consistent with the [Ansys workshop](https://innovationspace.ansys.com/courses/wp-content/uploads/2021/07/MAXW_GS_2020R2_EN_WS02.2.pdf). The independently written HFSS case uses public PyAEDT API concepts also documented in the official [PyAEDT waveguide example](https://examples.aedt.docs.pyansys.com/version/dev/examples/high_frequency/radiofrequency_mmwave/iris_filter.html); it does not copy that filter geometry, parameter set, narrative, or source implementation.

## Coupling and limitations

- G is a native AEDT loss link, not a copied scalar: Icepak's `MaxwellOhmicLoss` points to `BusbarDC / EMSetup : LastAdaptive`. With no heat-rejection wall, its high temperature proves link/solve connectivity only; it is not an engineering thermal prediction.
- H transfers Maxwell `TransferForce.Force_x` at scale 1.0 to Mechanical X force. Mechanical imported 621 nodes/80 elements, solved, and closed normally.
- E was not replaced by synthetic output. AEDT accepted the transient model/force parameter but rejected solving under the Student license.
- Coarse single-pass meshes keep cases within Student limits; adaptive warnings are preserved and acceptance is trend/tolerance based.

## Field dataset

Ten actual AEDT voltage solves (0.5-5 V) produced an NPZ with parameters, E, potential, labels, 81 coordinates and 64 quad rows. Connectivity is the exported structured sampling mesh, explicitly not proprietary adaptive FEM connectivity. Independent validation: **PASS**; normalized mean E/V relative span=2.84e-16. No model training was performed.

## Integrity

All case JSON/NPZ numbers are finite, relevant scripts compile, dataset indices/shapes pass, and the final AEDT process scan is empty. Checks: `{"phase0_pass": true, "maxwell_smoke_pass": true, "hfss_smoke_pass": true, "case_statuses_expected": true, "dataset_generation_pass": true, "dataset_validation_pass": true, "all_json_numeric_values_finite": true, "all_npz_arrays_finite": true, "scripts_compile": true, "no_residual_aedt_processes": true}`.
