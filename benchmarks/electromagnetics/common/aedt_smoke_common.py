"""Shared discovery, launch, reporting, and cleanup for AEDT Student smoke tests."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = Path(__import__("os").environ.get("AGENTIC_SIM_OUTPUT_DIR", ROOT / "outputs")) / "electromagnetics"
LOG_ROOT = Path(__import__("os").environ.get("AGENTIC_SIM_LOG_DIR", ROOT / "logs")) / "electromagnetics"


def ensure_dirs() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _distribution_version(*names: str) -> str | None:
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return None


def _version_info(executable: Path) -> dict[str, str | None]:
    script = (
        "$v=(Get-Item -LiteralPath $env:CODEX_AEDT_EXECUTABLE).VersionInfo;"
        "[pscustomobject]@{FileVersion=$v.FileVersion;ProductVersion=$v.ProductVersion;"
        "FileDescription=$v.FileDescription;ProductName=$v.ProductName;"
        "CompanyName=$v.CompanyName}|ConvertTo-Json -Compress"
    )
    process_env = os.environ.copy()
    process_env["CODEX_AEDT_EXECUTABLE"] = str(executable)
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        env=process_env,
        timeout=15,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"FileVersion": None, "ProductVersion": None, "FileDescription": None, "ProductName": None}


def _start_menu_targets() -> list[dict[str, str]]:
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    app_data = os.environ.get("APPDATA", "")
    menus = [Path(program_data) / "Microsoft/Windows/Start Menu/Programs"]
    if app_data:
        menus.append(Path(app_data) / "Microsoft/Windows/Start Menu/Programs")
    links = [
        str(path)
        for menu in menus
        if menu.exists()
        for path in menu.rglob("*.lnk")
        if re.search(r"ansys|electronics|aedt", path.name, re.IGNORECASE)
    ]
    if not links:
        return []
    script = (
        "$w=New-Object -ComObject WScript.Shell;"
        "$rows=@(foreach($p in $args){$s=$w.CreateShortcut($p);"
        "[pscustomobject]@{Link=$p;TargetPath=$s.TargetPath;Arguments=$s.Arguments;WorkingDirectory=$s.WorkingDirectory}});"
        "$rows|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script, *links],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    try:
        payload = json.loads(completed.stdout)
        return payload if isinstance(payload, list) else [payload]
    except json.JSONDecodeError:
        return []


def _process_executables() -> list[str]:
    try:
        import psutil
    except ImportError:
        return []
    result: list[str] = []
    for process in psutil.process_iter(["name", "exe"]):
        try:
            if (process.info["name"] or "").casefold() in {"ansysedt.exe", "ansysedtsv.exe"} and process.info["exe"]:
                result.append(process.info["exe"])
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return result


def discover_aedt() -> dict[str, Any]:
    """Discover AEDT from processes, environment, Start Menu, then narrow install patterns."""
    evidence: list[dict[str, str]] = []
    candidates: list[Path] = []
    for value in _process_executables():
        candidates.append(Path(value))
        evidence.append({"source": "running_process", "value": value})
    for key, value in os.environ.items():
        if re.fullmatch(r"ANSYSEM(?:SV)?_ROOT\d{3}", key, re.IGNORECASE) and value:
            root = Path(value)
            evidence.append({"source": f"environment:{key}", "value": value})
            candidates.extend(root / name for name in ("ansysedt.exe", "ansysedtsv.exe"))
    links = _start_menu_targets()
    for item in links:
        target = Path(item.get("TargetPath", ""))
        workdir = Path(item.get("WorkingDirectory", ""))
        evidence.append({"source": f"start_menu:{item.get('Link', '')}", "value": str(target)})
        for root in (target.parent, workdir):
            candidates.extend(root / name for name in ("ansysedt.exe", "ansysedtsv.exe"))
    bases = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ANSYS Inc/ANSYS Student",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "AnsysEM",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "ANSYS Inc/ANSYS Student",
    ]
    for base in bases:
        if not base.exists():
            continue
        roots = list(base.glob("v*/AnsysEM")) or [base]
        for root in roots:
            evidence.append({"source": "targeted_install_pattern", "value": str(root)})
            candidates.extend(root / name for name in ("ansysedt.exe", "ansysedtsv.exe"))
    existing: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key not in seen and candidate.is_file():
            seen.add(key)
            existing.append(candidate.resolve())
    existing.sort(key=lambda path: (path.name.casefold() != "ansysedtsv.exe", str(path)))
    trusted: list[tuple[Path, dict[str, str | None]]] = []
    rejected: list[dict[str, str]] = []
    temp_root = Path(tempfile.gettempdir()).resolve()
    for candidate in existing:
        reasons: list[str] = []
        if candidate.name.casefold() not in {"ansysedt.exe", "ansysedtsv.exe"}:
            reasons.append("unexpected executable name")
        if str(candidate).startswith("\\\\"):
            reasons.append("network path")
        if candidate.is_relative_to(ROOT.resolve()):
            reasons.append("repository path")
        if candidate.is_relative_to(temp_root):
            reasons.append("temporary path")
        version = _version_info(candidate)
        identity = " ".join(
            str(version.get(key) or "") for key in ("CompanyName", "ProductName", "FileDescription")
        )
        if "ansys" not in identity.casefold() or "electronics" not in identity.casefold():
            reasons.append("product metadata does not identify Ansys Electronics Desktop")
        if reasons:
            rejected.append({"path": str(candidate), "reason": "; ".join(reasons)})
        else:
            trusted.append((candidate, version))
    if not trusted:
        return {"found": False, "evidence": evidence, "executables": [], "rejected_candidates": rejected}
    executable, version_info = trusted[0]
    product_version = version_info.get("ProductVersion") or version_info.get("FileVersion") or ""
    match = re.match(r"(20\d{2})\.(\d)", product_version)
    release = f"{match.group(1)}.{match.group(2)}" if match else None
    internal = f"{match.group(1)[2:]}{match.group(2)}" if match else None
    return {
        "found": True,
        "installation_root": str(executable.parent),
        "executable": str(executable),
        "executable_name": executable.name,
        "is_student": executable.name.casefold() == "ansysedtsv.exe",
        "release": release,
        "internal_version": internal,
        "environment_variable": f"ANSYSEMSV_ROOT{internal}" if internal else None,
        "version_info": version_info,
        "executables": [str(path) for path, _ in trusted],
        "trust": {"status": "PASS", "checks": ["local path", "not repository/temp/network", "expected name", "Ansys product metadata"]},
        "rejected_candidates": rejected,
        "evidence": evidence,
    }


def configure_aedt_environment(discovery: dict[str, Any]) -> str:
    if not discovery.get("found"):
        raise RuntimeError("AEDT executable was not discovered")
    internal = discovery["internal_version"]
    key = f"ANSYSEMSV_ROOT{internal}" if discovery.get("is_student") else f"ANSYSEM_ROOT{internal}"
    os.environ[key] = discovery["installation_root"]
    return key


def prepare_pyaedt_student_runtime() -> dict[str, Any]:
    """Configure only the official PyAEDT Student launch parameters."""
    discovery = discover_aedt()
    env_key = configure_aedt_environment(discovery)
    return {
        "discovery": discovery,
        "injected_environment": {env_key: discovery["installation_root"]},
        "launch_policy": "official PyAEDT Student constructor; no monkey patches or manual server prelaunch",
    }


def student_launch_kwargs(runtime: dict[str, Any]) -> dict[str, Any]:
    """Return common PyAEDT constructor arguments for a new Student session."""
    return {
        "version": runtime["discovery"]["release"],
        "non_graphical": True,
        "new_desktop": True,
        "close_on_exit": True,
        "student_version": True,
    }


def aedt_processes() -> list[dict[str, Any]]:
    try:
        import psutil
    except ImportError:
        return []
    rows: list[dict[str, Any]] = []
    markers = ("ansysedt", "ansoft", "maxwell", "hfss")
    for process in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            haystack = " ".join([process.info.get("name") or "", process.info.get("exe") or ""]).casefold()
            if any(marker in haystack for marker in markers):
                rows.append(process.info)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return rows


def aedt_pid_set() -> set[int]:
    return {int(row["pid"]) for row in aedt_processes()}


def wait_for_process_exit(pid: int | None, timeout: float = 20.0) -> bool:
    if not pid:
        return True
    try:
        import psutil
        process = psutil.Process(pid)
        process.wait(timeout=timeout)
        return True
    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
        return not psutil.pid_exists(pid)


def cleanup_owned_process(pid: int | None) -> dict[str, Any]:
    """Terminate only the AEDT process launched by this smoke test and its children."""
    result: dict[str, Any] = {"pid": pid, "forced": False, "remaining": []}
    if not pid:
        return result
    try:
        import psutil
        parent = psutil.Process(pid)
    except (ImportError, psutil.NoSuchProcess):
        return result
    processes = parent.children(recursive=True) + [parent]
    for process in processes:
        try:
            process.terminate()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    _, alive = psutil.wait_procs(processes, timeout=10)
    if alive:
        result["forced"] = True
        for process in alive:
            try:
                process.kill()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
        _, alive = psutil.wait_procs(alive, timeout=5)
    result["remaining"] = [process.pid for process in alive]
    return result


def cleanup_new_aedt_processes(before: set[int]) -> list[dict[str, Any]]:
    """Clean AEDT processes created after a recorded baseline."""
    return [cleanup_owned_process(pid) for pid in sorted(aedt_pid_set() - before)]


def collect_phase0() -> dict[str, Any]:
    discovery = discover_aedt()
    package_version = _distribution_version("pyaedt", "ansys-aedt-core")
    module_available = importlib.util.find_spec("ansys.aedt.core") is not None
    gate = (
        "READY_FOR_LAUNCH_TEST"
        if discovery.get("found") and discovery.get("release") and package_version and module_available
        else "BLOCKED_AEDT_NOT_FOUND"
        if not discovery.get("found")
        else "BLOCKED_AEDT_VERSION_UNKNOWN"
        if not discovery.get("release")
        else "BLOCKED_PYAEDT_NOT_INSTALLED"
    )
    return {
        "phase": "Phase 0/1 - AEDT and PyAEDT environment check",
        "timestamp_utc": utc_now(),
        "status": "PASS" if gate == "READY_FOR_LAUNCH_TEST" else "FAIL",
        "gate": gate,
        "host": {
            "platform": platform.platform(),
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
            "ansys261_dir": os.environ.get("ANSYS261_DIR"),
        },
        "aedt": discovery,
        "pyaedt": {
            "distribution": "pyaedt",
            "version": package_version,
            "module": "ansys.aedt.core",
            "module_available": module_available,
        },
        "checks": {
            "aedt_student_executable_found": bool(discovery.get("found")),
            "release_confirmed": bool(discovery.get("release")),
            "pyaedt_distribution_found": package_version is not None,
            "pyaedt_import_target_found": module_available,
        },
        "processes_after_check": aedt_processes(),
    }


def base_smoke_result(kind: str, transport: str) -> dict[str, Any]:
    return {
        "test": kind,
        "timestamp_utc": utc_now(),
        "status": "FAIL",
        "transport": transport,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "pyaedt_version": _distribution_version("pyaedt", "ansys-aedt-core"),
    }
