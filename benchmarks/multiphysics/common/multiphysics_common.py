"""Shared infrastructure for Ansys 2026 R1 multiphysics smoke tests."""

from __future__ import annotations

import csv
import importlib
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from fluent_smoke_common import LOGS, OUT, ROOT, write_json


AWP_ROOT261 = Path(r"C:\Program Files\ANSYS Inc\ANSYS Student\v261")
SYSTEM_COUPLING_ROOT = AWP_ROOT261 / "SystemCoupling"
SYSTEM_COUPLING_LAUNCHER = SYSTEM_COUPLING_ROOT / "bin" / "systemcoupling.bat"
MAPDL_EXE = AWP_ROOT261 / "ansys" / "bin" / "winx64" / "ANSYS261.exe"
RUNTIME_CACHE = OUT / "runtime_cache"

_PROCESS_NAMES = {
    "systemcoupling.exe",
    "systemcouplingnode.exe",
    "cosimgui.exe",
    "fluent.exe",
    "fluent_aeneid.exe",
    "cortex.exe",
    "cx.exe",
    "ansys261.exe",
    "mapdl.exe",
}


def ensure_multiphysics_dirs() -> None:
    OUT.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    RUNTIME_CACHE.mkdir(parents=True, exist_ok=True)


def _import_pysystemcoupling() -> Any:
    """Import PySystemCoupling while keeping package caches in the workspace.

    ``appdirs`` uses the Windows shell API and ignores ``LOCALAPPDATA`` overrides.
    Redirecting its one import-time lookup avoids writes outside a sandboxed run.
    This does not alter the environment inherited by Ansys participant processes.
    """
    ensure_multiphysics_dirs()
    try:
        return importlib.import_module("ansys.systemcoupling.core")
    except PermissionError as first_error:
        import appdirs

        original = appdirs.user_data_dir
        appdirs.user_data_dir = lambda *args, **kwargs: str(RUNTIME_CACHE / "pysystemcoupling")
        try:
            return importlib.import_module("ansys.systemcoupling.core")
        except Exception:
            raise first_error
        finally:
            appdirs.user_data_dir = original


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for distribution in (
        "ansys-systemcoupling-core",
        "ansys-mapdl-core",
        "ansys-fluent-core",
        "protobuf",
        "grpcio-health-checking",
        "grpcio-reflection",
    ):
        try:
            from importlib.metadata import version

            versions[distribution] = version(distribution)
        except Exception:
            versions[distribution] = None
    return versions


def multiphysics_processes() -> list[dict[str, str | int]]:
    """Return conservative System Coupling, Fluent, and MAPDL process data."""
    completed = subprocess.run(
        ["tasklist", "/fo", "csv", "/nh"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    rows: list[dict[str, str | int]] = []
    for row in csv.reader(completed.stdout.splitlines()):
        if len(row) < 2 or row[0].lower() not in _PROCESS_NAMES:
            continue
        try:
            pid = int(row[1])
        except ValueError:
            pid = -1
        rows.append({"name": row[0], "pid": pid})
    return rows


def new_processes_since(before: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
    baseline = {(str(item["name"]).lower(), int(item["pid"])) for item in before}
    return [
        item
        for item in multiphysics_processes()
        if (str(item["name"]).lower(), int(item["pid"])) not in baseline
    ]


def wait_for_process_cleanup(
    before: list[dict[str, str | int]], timeout: float = 20.0
) -> list[dict[str, str | int]]:
    deadline = time.monotonic() + timeout
    remaining = new_processes_since(before)
    while remaining and time.monotonic() < deadline:
        time.sleep(0.5)
        remaining = new_processes_since(before)
    return remaining


@contextmanager
def system_coupling_session(
    *, working_dir: Path | None = None, start_output: bool = False, **kwargs: Any
) -> Iterator[Any]:
    """Launch System Coupling 261 and guarantee a graceful shutdown.

    The loopback-only insecure transport avoids System Coupling's otherwise
    mandatory ``%USERPROFILE%/.conn`` write, which is unavailable in restricted
    automation runners. Callers can still pass an explicit ``connection_type``.
    """
    if not SYSTEM_COUPLING_LAUNCHER.is_file():
        raise FileNotFoundError(f"System Coupling launcher not found: {SYSTEM_COUPLING_LAUNCHER}")
    pysyc = _import_pysystemcoupling()
    if "connection_type" not in kwargs:
        kwargs["connection_type"] = pysyc.ConnectionType.INSECURE_LOCAL
    run_dir = (working_dir or OUT / "system_coupling").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    child_overrides = {
        "AWP_ROOT261": str(AWP_ROOT261),
        # The 261 launcher prints a copyright symbol before starting the
        # controller. A GBK console otherwise raises UnicodeEncodeError.
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    old_environment = {key: os.environ.get(key) for key in child_overrides}
    os.environ.update(child_overrides)
    try:
        session = pysyc.launch(
            version="261", working_dir=str(run_dir), start_output=start_output, **kwargs
        )
    finally:
        for key, old_value in old_environment.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value
    try:
        yield session
    finally:
        try:
            session.exit()
        except Exception:
            pass


@contextmanager
def mapdl_session(*, working_dir: Path | None = None, **kwargs: Any) -> Iterator[Any]:
    """Launch the local Student MAPDL 261 service and guarantee shutdown."""
    if not MAPDL_EXE.is_file():
        raise FileNotFoundError(f"MAPDL executable not found: {MAPDL_EXE}")
    import ansys.mapdl.core as pymapdl

    run_dir = (working_dir or OUT / "mapdl").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    session = pymapdl.launch_mapdl(
        exec_file=str(MAPDL_EXE),
        run_location=str(run_dir),
        nproc=1,
        override=True,
        cleanup_on_exit=True,
        **kwargs,
    )
    try:
        yield session
    finally:
        try:
            session.exit()
        except Exception:
            pass


__all__ = [
    "AWP_ROOT261",
    "LOGS",
    "MAPDL_EXE",
    "OUT",
    "ROOT",
    "SYSTEM_COUPLING_LAUNCHER",
    "SYSTEM_COUPLING_ROOT",
    "ensure_multiphysics_dirs",
    "multiphysics_processes",
    "mapdl_session",
    "new_processes_since",
    "package_versions",
    "system_coupling_session",
    "wait_for_process_cleanup",
    "write_json",
]
