"""Guard the declared Python 3.10 syntax floor from newer-only grammar."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TREES = ("src", "benchmarks", "tools", "tests")


def test_python_sources_parse_as_python310() -> None:
    failures: list[str] = []
    for tree in SOURCE_TREES:
        for path in sorted((ROOT / tree).rglob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))
            except SyntaxError as exc:
                failures.append(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

    assert failures == []
