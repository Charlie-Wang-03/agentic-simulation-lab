"""Statically enforce the repository subprocess safety baseline."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "src", ROOT / "benchmarks", ROOT / "tools", ROOT / "tests")
BOUNDED_CALLS = {"run", "call", "check_call", "check_output"}


def main() -> int:
    errors: list[str] = []
    for base in SCAN_ROOTS:
        for path in base.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: cannot audit subprocesses: {exc}")
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                owner = node.func.value
                if not isinstance(owner, ast.Name):
                    continue
                name = node.func.attr
                keywords = {item.arg: item.value for item in node.keywords if item.arg}
                relative = path.relative_to(ROOT).as_posix()
                if owner.id == "os" and name == "system":
                    errors.append(f"{relative}:{node.lineno}: os.system is forbidden")
                if owner.id != "subprocess":
                    continue
                shell = keywords.get("shell")
                if isinstance(shell, ast.Constant) and shell.value is True:
                    errors.append(f"{relative}:{node.lineno}: shell=True is forbidden")
                if name in BOUNDED_CALLS and "timeout" not in keywords:
                    errors.append(f"{relative}:{node.lineno}: subprocess.{name} requires a timeout")
    for error in errors:
        print(error)
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
