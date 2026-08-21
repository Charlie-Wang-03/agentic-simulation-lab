"""Phase 0: verify the local PySystemCoupling-to-System Coupling 261 link."""

from __future__ import annotations

from datetime import datetime, timezone

from multiphysics_common import (
    OUT,
    SYSTEM_COUPLING_LAUNCHER,
    multiphysics_processes,
    package_versions,
    system_coupling_session,
    wait_for_process_cleanup,
    write_json,
)


CASE = "system_coupling_connect"


def main() -> int:
    before = multiphysics_processes()
    payload = {
        "case": CASE,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "launcher": str(SYSTEM_COUPLING_LAUNCHER),
        "launcher_found": SYSTEM_COUPLING_LAUNCHER.is_file(),
        "packages": package_versions(),
        "processes_before": before,
    }
    try:
        with system_coupling_session(working_dir=OUT / CASE) as syc:
            payload["ping"] = bool(syc.ping())
            payload["server_version"] = syc.version
        remaining = wait_for_process_cleanup(before)
        payload["residual_processes"] = remaining
        checks = {
            "launcher_found": payload["launcher_found"],
            "import_available": payload["packages"]["ansys-systemcoupling-core"] is not None,
            "ping": payload["ping"],
            "server_is_26_1": payload["server_version"] == "26.1",
            "clean_shutdown": not remaining,
        }
        payload["checks"] = checks
        payload["status"] = "PASS" if all(checks.values()) else "FAIL"
    except Exception as exc:
        payload.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
        payload["residual_processes"] = wait_for_process_cleanup(before)
    write_json(OUT / f"{CASE}.json", payload)
    print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
