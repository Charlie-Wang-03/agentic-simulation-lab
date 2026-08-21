from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / "docs" / "tutorials"


def main() -> int:
    errors: list[str] = []
    english = {path.stem for path in TUTORIALS.glob("*.md") if not path.name.endswith(".zh-CN.md")}
    chinese = {path.name.removesuffix(".zh-CN.md") for path in TUTORIALS.glob("*.zh-CN.md")}
    for missing in sorted(english - chinese):
        errors.append(f"missing Chinese tutorial pair: {missing}.zh-CN.md")
    for missing in sorted(chinese - english):
        errors.append(f"missing English tutorial pair: {missing}.md")
    for error in errors:
        print(error)
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
