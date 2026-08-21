"""Phase 0: minimal PyFluent -> Fluent 261 automation-chain smoke test."""

from __future__ import annotations

import time

import ansys.fluent.core as pyfluent

from fluent_smoke_common import (
    FLUENT_EXE,
    LOGS,
    OUT,
    base_payload,
    ensure_dirs,
    fluent_processes,
    launch_fluent,
    tui,
    write_json,
)


CASE = "fluent_phase0_connect"


def main() -> int:
    ensure_dirs()
    before = fluent_processes()
    payload = base_payload(CASE, "Fluent automation connection")
    payload["before_processes"] = before
    payload["pyfluent_import"] = True
    payload["pyfluent_version"] = pyfluent.__version__
    payload["fluent_executable_exists"] = FLUENT_EXE.is_file()
    session = None
    try:
        session = launch_fluent(dimension=2, processor_count=2, cwd=OUT)
        product_version = str(session.get_fluent_version())
        health = str(session.health_check.status())
        api_result = str(tui(session, "/report/system/proc-stats"))
        payload.update(
            {
                "fluent_product_version": product_version,
                "health_check": health,
                "minimal_tui_command": "/report/system/proc-stats",
                "minimal_tui_return": api_result,
            }
        )
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if session is not None:
            try:
                session.exit()
            except Exception as exc:
                payload["exit_error"] = f"{type(exc).__name__}: {exc}"
        # Fluent's parallel host/node processes can need several seconds to reap.
        time.sleep(10.0)
        after = fluent_processes()
        payload["after_processes"] = after
        new_processes = [p for p in after if p not in before]
        payload["new_residual_processes"] = new_processes
        checks = {
            "pyfluent_import": payload.get("pyfluent_import") is True,
            "executable_found": payload.get("fluent_executable_exists") is True,
            "version_261": any(
                marker in payload.get("fluent_product_version", "")
                for marker in ("2026 R1", "26.1", "261")
            ),
            "health_serving": "serving" in payload.get("health_check", "").lower(),
            "tui_executed": "error" not in payload and "minimal_tui_return" in payload,
            "clean_exit": not new_processes,
        }
        payload["checks"] = checks
        payload["status"] = "PASS" if all(checks.values()) else "FAIL"
        result_path = write_json(OUT / f"{CASE}.json", payload)
        print(f"RESULT_JSON={result_path}")
        print(f"STATUS={payload['status']}")
        print(payload)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
