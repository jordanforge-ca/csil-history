#!/usr/bin/env python3
"""Fail when a publicly readable source has no usable copy to open.

Run from the repository root:

    python3 scripts/check_source_access.py

Quarto also runs this before render. A failing record is named with the
front-matter field that is missing or unusable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from source_access import iter_source_records, validate_record


def check_root(root: Path) -> list[str]:
    sources = root / "sources"
    if not sources.is_dir():
        return [f"{root}: no sources/ directory to check"]
    errors: list[str] = []
    records = iter_source_records(root)
    if not records:
        errors.append(f"{sources}: no source records found")
    for record in records:
        errors.extend(validate_record(record, root))
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    errors = check_root(root)
    if errors:
        print(f"Source access check failed ({len(errors)} problem(s)):\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    count = len(iter_source_records(root))
    print(f"Source access check passed for {count} source record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
