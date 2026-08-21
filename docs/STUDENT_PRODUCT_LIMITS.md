# Student product limits

Checked against official sources: 2026-08-21

Always verify the current download page and installed clickwrap. Limits can change by release and product.

## Current general Student guidance

The official [Ansys Student download page](https://www.ansys.com/en-gb/home/academic/students/ansys-student) currently lists Windows 10/11 64-bit for Ansys Student, a renewable twelve-month lease from release, up to four CPU cores for HPC solutions, 128,000 structural nodes/elements, and one million fluid cells/nodes. It also lists Rocky Student limits of 32,000 DEM particles, 128,000 SPH elements, no GPU, and limited modules/scripts.

Current [Ansys academic usage terms](https://www.ansys.com/legal/terms-and-conditions/academic-usage) distinguish free Student downloads and Teaching/EduPack programs from Research and Associate programs. Free Student downloads are limited to student instruction, student projects, and student demonstrations. Academic programs exclude commercial activity and competitive analysis. Users must follow the category and conditions actually granted to them; Student must not be described as a blanket academic-research license.

## Product-specific observations

- Mechanical/MAPDL and Fluent cases in this repository are deliberately small, but users must check their own release limits.
- AEDT Student has product-specific limitations; see the official [HFSS Student limitations](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Content/GettingStarted/HFSSStudentLimitations.htm). The catalog preserves an observed Maxwell Transient `BLOCKED` result.
- Rocky two-way CFD–DEM and selected SPH workflows remain `BLOCKED` where the observed Student/API combination did not expose the required capability.
- System Coupling requires available participant solvers and compatible licenses; a participant or license absence is `BLOCKED`.
- Chemistry, turbulence, multiphase, contact, and coupled results remain model-dependent even when the product allows them.

## Platform statement

Local Student solver execution is supported here on Windows only. The core package, catalogs, reports, dry-runs, and static validation are cross-platform. macOS local Student solver execution is not claimed. Official PyMAPDL documentation states that the Python client can install on macOS while MAPDL itself is not macOS-compatible; remote/container arrangements require their own valid license and configuration.
