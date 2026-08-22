"""Statically enforce the repository subprocess safety baseline."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "src", ROOT / "benchmarks", ROOT / "tools", ROOT / "tests")
BOUNDED_CALLS = {"run", "call", "check_call", "check_output"}


def _import_bindings(tree: ast.AST) -> tuple[set[str], dict[str, str], set[str], set[str]]:
    subprocess_modules: set[str] = set()
    subprocess_calls: dict[str, str] = {}
    os_modules: set[str] = set()
    os_system_calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                local_name = item.asname or item.name
                if item.name == "subprocess":
                    subprocess_modules.add(local_name)
                elif item.name == "os":
                    os_modules.add(local_name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                for item in node.names:
                    if item.name != "*":
                        subprocess_calls[item.asname or item.name] = item.name
            elif node.module == "os":
                for item in node.names:
                    if item.name == "system":
                        os_system_calls.add(item.asname or item.name)
    return subprocess_modules, subprocess_calls, os_modules, os_system_calls


def audit_source(source: str, *, relative: str = "<source>") -> list[str]:
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as exc:
        return [f"{relative}: cannot audit subprocesses: {exc}"]
    subprocess_modules, subprocess_calls, os_modules, os_system_calls = _import_bindings(tree)
    errors: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module in {"os", "subprocess"}
            and any(item.name == "*" for item in node.names)
        ):
            errors.append(f"{relative}:{node.lineno}: {node.module} star import is forbidden")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        api_name: str | None = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            owner = node.func.value.id
            if owner in os_modules and node.func.attr == "system":
                errors.append(f"{relative}:{node.lineno}: os.system is forbidden")
                continue
            if owner in subprocess_modules:
                api_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            if node.func.id in os_system_calls:
                errors.append(f"{relative}:{node.lineno}: os.system is forbidden")
                continue
            api_name = subprocess_calls.get(node.func.id)
        if api_name is None:
            continue
        keywords = {item.arg: item.value for item in node.keywords if item.arg}
        shell = keywords.get("shell")
        if shell is not None and not (isinstance(shell, ast.Constant) and shell.value is False):
            errors.append(
                f"{relative}:{node.lineno}: subprocess.{api_name} shell must be statically False"
            )
        if any(item.arg is None for item in node.keywords):
            errors.append(
                f"{relative}:{node.lineno}: subprocess.{api_name} dynamic keyword arguments are forbidden"
            )
        if api_name in BOUNDED_CALLS and "timeout" not in keywords:
            errors.append(f"{relative}:{node.lineno}: subprocess.{api_name} requires a timeout")
    return errors


def main() -> int:
    errors: list[str] = []
    for base in SCAN_ROOTS:
        for path in base.rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{path.relative_to(ROOT).as_posix()}: cannot audit subprocesses: {exc}")
                continue
            errors.extend(audit_source(source, relative=relative))
    for error in errors:
        print(error)
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
