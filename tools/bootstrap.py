"""Create and populate the project-local virtual environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"


def environment_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extras",
        default="dev",
        help="comma-separated optional dependency groups; use an empty value for core only",
    )
    parser.add_argument("--offline", action="store_true", help="disable package-index access")
    parser.add_argument("--no-install", action="store_true", help="create the environment without installing the project")
    args = parser.parse_args(argv)

    if not VENV.exists():
        venv.EnvBuilder(with_pip=True).create(VENV)
    if args.no_install:
        print(environment_python())
        return 0

    requirement = "." if not args.extras else f".[{args.extras}]"
    command = [str(environment_python()), "-m", "pip", "install", "-e", requirement]
    if args.offline:
        command.extend(["--no-index"])
    completed = subprocess.run(command, cwd=ROOT, check=False, timeout=900)
    if completed.returncode:
        print("Project installation failed; review pip output without changing validation thresholds.", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
