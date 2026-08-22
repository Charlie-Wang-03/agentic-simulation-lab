"""Minimal official PyAEDT Student HFSS create/save/close smoke test."""

from __future__ import annotations

import argparse
import traceback

from aedt_smoke_common import (
    OUTPUT_ROOT,
    aedt_processes,
    base_smoke_result,
    cleanup_owned_process,
    ensure_dirs,
    prepare_pyaedt_student_runtime,
    student_launch_kwargs,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphical", action="store_true", help="requires explicit interactive-run authorization")
    args = parser.parse_args()
    ensure_dirs()
    result = base_smoke_result("HFSS connection smoke", "official-pyaedt")
    result_path = OUTPUT_ROOT / "smoke" / "hfss_connect_official.json"
    app = None
    owned_pid = None
    try:
        runtime = prepare_pyaedt_student_runtime()
        result["runtime"] = runtime
        from ansys.aedt.core import Hfss

        kwargs = student_launch_kwargs(runtime)
        kwargs["non_graphical"] = not args.graphical
        app = Hfss(
            project="HfssConnectSmoke",
            design="HFSS_Smoke",
            solution_type="Modal",
            **kwargs,
        )
        owned_pid = getattr(app.desktop_class, "aedt_process_id", None)
        project_file = OUTPUT_ROOT / "smoke" / "hfss_connect_smoke.aedt"
        save_ok = bool(app.save_project(project_file))
        result.update({
            "status": "PASS" if save_ok else "FAIL",
            "aedt_process_id": owned_pid,
            "project_saved": bool(save_ok and project_file.exists()),
            "launch_strategy": "official_pyaedt_student_constructor",
        })
    except Exception as exc:  # noqa: BLE001 - durable solver evidence must capture API failures
        message = f"{type(exc).__name__}: {exc}"
        result["status"] = "BLOCKED" if any(
            word in message.casefold() for word in ("license", "not found", "student")
        ) else "FAIL"
        result["error"] = message
        result["traceback"] = traceback.format_exc()
    finally:
        if app is not None:
            try:
                result["release_return"] = app.release_desktop(close_projects=True, close_desktop=True)
            except Exception as exc:  # noqa: BLE001
                result["release_error"] = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = cleanup_owned_process(owned_pid)
        result["processes_after_close"] = aedt_processes()
        if result["cleanup"]["remaining"]:
            result["status"] = "FAIL"
        write_json(result_path, result)
        print(result)
    return 0 if result["status"] in {"PASS", "BLOCKED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
