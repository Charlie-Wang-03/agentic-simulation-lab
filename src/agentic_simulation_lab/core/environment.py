from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import platform
import shutil
from pathlib import Path

from .paths import project_root

PROBES = {
    "mechanical": "ansys.mechanical.core",
    "fluent": "ansys.fluent.core",
    "mapdl": "ansys.mapdl.core",
    "aedt": "ansys.aedt.core",
    "rocky": "ansys.rocky.core",
    "system_coupling": "ansys.systemcoupling.core",
}

DISTRIBUTIONS = {
    "mechanical": "ansys-mechanical-core", "fluent": "ansys-fluent-core",
    "mapdl": "ansys-mapdl-core", "aedt": "pyaedt",
    "rocky": "ansys-rocky-core", "system_coupling": "ansys-systemcoupling-core",
}


def inspect_environment(probe: str | None = None) -> dict[str, object]:
    packages = {}
    for name, module in PROBES.items():
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError):
            found = False
        try:
            version = importlib.metadata.version(DISTRIBUTIONS[name]) if found else None
        except importlib.metadata.PackageNotFoundError:
            version = None
        packages[name] = {"status": "FOUND" if found else "MISSING", "version": version}
    ansys_root_text = os.environ.get("AWP_ROOT261")
    aedt_root_text = os.environ.get("ANSYSEMSV_ROOT252") or os.environ.get("ANSYSEM_ROOT252")
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    if not aedt_root_text:
        discovered_aedt = sorted((program_files / "ANSYS Inc" / "ANSYS Student").glob("v*/AnsysEM/ansysedtsv.exe"))
        if discovered_aedt:
            aedt_root_text = str(discovered_aedt[-1].parent)
    ansys_root = Path(ansys_root_text) if ansys_root_text else None
    aedt_root = Path(aedt_root_text) if aedt_root_text else None
    candidates = {
        "mechanical": ansys_root / "aisol" / "bin" / "winx64" / "AnsysWBU.exe" if ansys_root else None,
        "mapdl": ansys_root / "ansys" / "bin" / "winx64" / "ANSYS261.exe" if ansys_root else None,
        "fluent": ansys_root / "fluent" / "ntbin" / "win64" / "fluent.exe" if ansys_root else None,
        "system_coupling": ansys_root / "SystemCoupling" / "bin" / "systemcoupling.bat" if ansys_root else None,
        "rocky": ansys_root / "rocky" / "bin" / "Rocky.exe" if ansys_root else None,
        "aedt": aedt_root / "ansysedtsv.exe" if aedt_root else None,
    }
    executables = {}
    for name, candidate in candidates.items():
        path = str(candidate) if candidate and candidate.is_file() else shutil.which(candidate.name) if candidate else None
        executables[name] = {"status": "FOUND" if path else "MISSING", "path": path}
    result: dict[str, object] = {
        "python": {"status": "FOUND", "version": platform.python_version(), "executable": "current interpreter"},
        "platform": platform.platform(), "project_root": str(project_root()), "packages": packages,
        "configured_root": os.environ.get("AGENTIC_SIMULATION_LAB_ROOT"),
        "student_roots": {"ansys": ansys_root_text, "aedt": aedt_root_text},
        "executables": executables,
    }
    if probe:
        result["probe"] = {"target": probe, "status": "STATIC_ONLY", "solver_launched": False}
    return result
