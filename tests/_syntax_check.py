"""Compile-check every Python source under services/, apps/, and packages/."""

from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOTS = ("services", "apps", "packages")
SKIP_PARTS = ("node_modules", ".venv", "dist", "build", "__pycache__", ".turbo")


def main() -> int:
    errors: list[tuple[Path, str]] = []
    scanned = 0
    for root in ROOTS:
        for path in Path(root).rglob("*.py"):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            scanned += 1
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as e:
                msg = (e.msg or str(e)).splitlines()[-1]
                errors.append((path, msg))
    print(f"scanned={scanned} errors={len(errors)}")
    for path, msg in errors:
        print(f"  {path}: {msg}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
