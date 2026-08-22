# Third-party dependency notices

Checked: 2026-08-22

No third-party source code, official Ansys examples, Ansys binaries, Ansys documentation copies, or third-party datasets are vendored in the candidate public tree. The dependencies below are declarations only: installers resolve them separately from their package indexes, and each remains governed by its own license and packaged notices.

| Direct declaration | Role | Upstream project license | Optional | Separately licensed proprietary runtime required |
|---|---|---|---|---|
| `ansys-mechanical-core` | Mechanical interoperability | MIT | Yes (`mechanical`) | Yes, for solver execution |
| `ansys-fluent-core` | Fluent interoperability | MIT | Yes (`fluent`) | Yes, for solver execution |
| `ansys-mapdl-core` | MAPDL interoperability | MIT | Yes (`mapdl`) | Yes, for solver execution |
| `pyaedt` | AEDT interoperability | MIT | Yes (`aedt`) | Yes, for solver execution |
| `ansys-rocky-core` | Rocky interoperability | MIT | Yes (`rocky`) | Yes, for solver execution |
| `ansys-systemcoupling-core` | System Coupling interoperability | MIT | Yes (`system-coupling`) | Yes, including participant-product licenses for coupled execution |
| `numpy` | Dataset arrays, simulation-result plotting, and development tests | BSD-3-Clause main project; distributions carry their own complete component notices | Yes (`data`, `visuals`, `dev`) | No |
| `pandas` | Tabular dataset workflows | BSD-3-Clause main project; distributions carry their own complete component notices | Yes (`data`) | No |
| `matplotlib` | Deterministic paper-style simulation-result figures | PSF-based Matplotlib license; distributions carry their own complete component notices | Yes (`visuals`, `dev`) | No |
| `pillow` | PNG writing and provenance-metadata checks | HPND | Yes (`visuals`, `dev`) | No |
| `pytest` | Tests | MIT | Development only | No |
| `ruff` | Linting | MIT, with bundled-component notices in its distribution | Development only | No |
| `build` | PEP 517 package builds | MIT | Development only | No |
| `setuptools` | Build backend and development tooling | MIT | Build/development only | No |
| `wheel` | Wheel inspection/tooling | MIT | Development only | No |

The core package has no mandatory runtime dependency. Optional PyAnsys clients remain lazily imported. Installing an open-source client never supplies, licenses, or changes the license of an Ansys product. Solver execution requires separately obtained Ansys software and a license appropriate for the intended use.

Current upstream package metadata supports the project’s Python 3.10 baseline for the declared clients and tools, subject to each resolved release. Current pandas development metadata targets Python 3.11 and newer; on Python 3.10, package installers must select a still-compatible pandas release rather than bypass upstream `Requires-Python` metadata.

Primary project sources used for this audit:

- <https://github.com/ansys/pymechanical>
- <https://github.com/ansys/pyfluent>
- <https://github.com/ansys/pymapdl>
- <https://github.com/ansys/pyaedt>
- <https://github.com/ansys/pyrocky>
- <https://github.com/ansys/pysystem-coupling>
- <https://github.com/numpy/numpy>
- <https://github.com/pandas-dev/pandas>
- <https://github.com/matplotlib/matplotlib>
- <https://github.com/python-pillow/Pillow>
- <https://github.com/pytest-dev/pytest>
- <https://github.com/astral-sh/ruff>
- <https://github.com/pypa/build>, <https://github.com/pypa/setuptools>, and <https://github.com/pypa/wheel>

The seven small STL files under `assets/rocky/` are original repository fixtures generated as simple educational geometry. Their exact hashes and ownership classification are recorded in [the source-provenance audit](docs/release/SOURCE_PROVENANCE.md).
