"""Launch the particle free-fall case through Rocky's headless script API."""

from __future__ import annotations

import os
from pathlib import Path

from rocky_smoke_common import read_json, run_rocky_script

SCRIPT = Path(__file__).with_name("smoke_particle_freefall.py")


def main() -> int:
    launch = run_rocky_script(SCRIPT, case_name="particle_freefall", timeout_s=600)
    output_root = Path(os.environ["AGENTIC_SIM_OUTPUT_DIR"])
    result_path = output_root / "rocky_dem" / "case_a_freefall" / "result.json"
    if launch["timed_out"] or launch["return_code"] != 0 or not result_path.is_file():
        return 1
    return 0 if read_json(result_path).get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
