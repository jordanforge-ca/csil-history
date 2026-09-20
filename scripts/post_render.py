#!/usr/bin/env python3
"""Post-render HTML fixes that Quarto website templates do not provide.

Injects a skip-to-content link as the first child of <body> so keyboard
users can bypass the navbar. Safe to run more than once.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP = (
    '<a class="skip-link" href="#quarto-document-content">'
    "Skip to main content</a>\n"
)
SKIP_RE = re.compile(
    r'<a class="skip-link"[^>]*>.*?</a>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
BODY_RE = re.compile(r"<body[^>]*>", flags=re.IGNORECASE)


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    text = SKIP_RE.sub("", text)
    match = BODY_RE.search(text)
    if not match:
        return False
    insert_at = match.end()
    text = text[:insert_at] + "\n" + SKIP + text[insert_at:]
    path.write_text(text, encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    site_root = Path(argv[1] if len(argv) > 1 else "_site")
    if not site_root.is_dir():
        print(f"No site directory at {site_root}", file=sys.stderr)
        return 2
    count = 0
    for path in sorted(site_root.rglob("*.html")):
        if "site_libs" in path.parts:
            continue
        if patch(path):
            count += 1
    print(f"Injected skip link into {count} HTML page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
