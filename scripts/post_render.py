#!/usr/bin/env python3
"""Post-render HTML fixes for the accessibility baseline.

Quarto's default website chrome is close, but not sufficient. This script
runs after every `quarto render` and:

1. Injects a skip link as the first child of <body>
2. Makes main a skip-link target (tabindex="-1")
3. Labels landmark <nav> elements
4. Sets aria-current="page" from the real path (not Quarto's nearest-item guess)
5. Adds visually hidden "(current page)" text
6. Captions listing tables and adds scope="col" to header cells
7. Calls out external / PDF links in accessible text
8. Removes the empty sidebar-expand <a> (duplicate of the toggle button)

Standard library only. Safe to run more than once.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP = (
    '<a class="skip-link" href="#quarto-document-content">'
    "Skip to main content</a>\n"
)
CURRENT = '<span class="visually-hidden"> (current page)</span>'
EXTERNAL = '<span class="visually-hidden"> (external site)</span>'
PDF = '<span class="visually-hidden"> (PDF)</span>'

SKIP_RE = re.compile(
    r'<a class="skip-link"[^>]*>.*?</a>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)
BODY_RE = re.compile(r"<body[^>]*>", flags=re.IGNORECASE)
CURRENT_RE = re.compile(
    r'\s*<span class="visually-hidden"> \(current page\)</span>',
)
EXTERNAL_RE = re.compile(
    r'\s*<span class="visually-hidden"> \(external site\)</span>',
)
PDF_RE = re.compile(r'\s*<span class="visually-hidden"> \(PDF\)</span>')
EMPTY_SIDEBAR_A_RE = re.compile(
    r'<a class="flex-grow-1" role="navigation"[^>]*>\s*</a>',
    flags=re.IGNORECASE,
)
MAIN_RE = re.compile(
    r'<main([^>]*id="quarto-document-content"[^>]*)>',
    flags=re.IGNORECASE,
)
NAV_LABELS = (
    ('<nav class="navbar navbar-expand-lg', "Primary"),
    ('<nav class="quarto-secondary-nav"', "Section menu"),
    ('<nav id="quarto-sidebar"', "In this section"),
    ('<nav id="TOC"', "On this page"),
    ('<nav class="page-navigation"', "Previous and next pages"),
)

PAGE_TABLE_CAPTION = {
    "sources/index.html": "Annotated source catalogue",
    "people/index.html": "People with stub pages in this archive",
    "research/wanted-sources.html": "Wanted source catalogue records",
}

INTERNAL_HOSTS = (
    "jordanforge-ca.github.io",
    "127.0.0.1",
    "localhost",
)


def page_key(path: Path, site_root: Path) -> str:
    return path.relative_to(site_root).as_posix()


def primary_current_target(rel: str) -> str | None:
    if rel == "index.html":
        return "brand"
    if rel == "404.html":
        return None
    if rel == "timeline.html":
        return "timeline.html"
    if rel.startswith("history/"):
        return "history/index.html"
    if rel.startswith("sources/"):
        return "sources/index.html"
    if rel.startswith("people/"):
        return "people/index.html"
    if rel.startswith("organizations/"):
        return "organizations/index.html"
    if rel.startswith("research/"):
        return "research/wanted-sources.html"
    if rel.startswith("docs/") or rel == "about.html":
        return "about.html"
    return None


def strip_attr(html: str, attr: str) -> str:
    return re.sub(rf'\s+{attr}="[^"]*"', "", html)


def ensure_attr(open_tag: str, attr: str, value: str) -> str:
    pattern = rf'{attr}="'
    if pattern in open_tag:
        return re.sub(rf'{attr}="[^"]*"', f'{attr}="{value}"', open_tag, count=1)
    return open_tag[:-1] + f' {attr}="{value}">'


def inject_skip_and_main(html: str) -> str:
    html = SKIP_RE.sub("", html)
    match = BODY_RE.search(html)
    if match:
        html = html[: match.end()] + "\n" + SKIP + html[match.end() :]

    def _main(m: re.Match[str]) -> str:
        tag = "<main" + m.group(1) + ">"
        if "tabindex=" not in tag:
            tag = ensure_attr(tag, "tabindex", "-1")
        return tag

    return MAIN_RE.sub(_main, html, count=1)


def label_landmarks(html: str) -> str:
    for prefix, label in NAV_LABELS:
        idx = html.find(prefix)
        if idx == -1:
            continue
        end = html.find(">", idx)
        if end == -1:
            continue
        tag = html[idx : end + 1]
        if "aria-label=" not in tag:
            tag = tag[:-1] + f' aria-label="{label}">'
            html = html[:idx] + tag + html[end + 1 :]
    return html


def mark_current_page(html: str, rel: str) -> str:
    html = CURRENT_RE.sub("", html)
    html = re.sub(r'\saria-current="page"', "", html)
    target = primary_current_target(rel)
    if not target:
        return html

    if target == "brand":

        def _brand(m: re.Match[str]) -> str:
            tag = m.group(0)
            tag = ensure_attr(tag, "aria-current", "page")
            return tag

        html = re.sub(
            r'<a class="navbar-brand"[^>]*>',
            _brand,
            html,
            count=1,
        )
        html = re.sub(
            r'(<a class="navbar-brand"[^>]*>)(.*?)(</a>)',
            lambda m: m.group(1) + m.group(2) + CURRENT + m.group(3),
            html,
            count=1,
            flags=re.DOTALL,
        )
        return html

    def replace_navbar_block(block: str) -> str:
        def one_link(m: re.Match[str]) -> str:
            start, href, mid, inner, end = (
                m.group(1),
                m.group(2),
                m.group(3),
                m.group(4),
                m.group(5),
            )
            url = href.split('"', 1)[-1].rstrip('"')
            if url.endswith(target) or url.endswith("/" + target):
                mid = strip_attr(mid, "aria-current")
                if "aria-current=" not in mid:
                    mid = mid[:-1] + ' aria-current="page">'
                if CURRENT not in inner:
                    inner = inner + CURRENT
            return start + href + mid + inner + end

        return re.sub(
            r'(<a class="nav-link[^"]*")( href="[^"]+")([^>]*>)(.*?)(</a>)',
            one_link,
            block,
            flags=re.DOTALL,
        )

    nav_match = re.search(
        r'<nav class="navbar[^"]*"[^>]*>.*?</nav>', html, flags=re.DOTALL
    )
    if nav_match:
        html = (
            html[: nav_match.start()]
            + replace_navbar_block(nav_match.group(0))
            + html[nav_match.end() :]
        )

    def sidebar_link(m: re.Match[str]) -> str:
        start, inner, end = m.group(1), m.group(2), m.group(3)
        if "sidebar-link active" in start or 'class="sidebar-item-text sidebar-link active"' in start:
            if "aria-current=" not in start:
                start = start[:-1] + ' aria-current="page">'
            if CURRENT not in inner:
                inner = inner + CURRENT
        return start + inner + end

    html = re.sub(
        r'(<a href="[^"]*" class="sidebar-item-text sidebar-link[^"]*"[^>]*>)(.*?)(</a>)',
        sidebar_link,
        html,
        flags=re.DOTALL,
    )
    return html


def caption_tables(html: str, rel: str) -> str:
    specific = PAGE_TABLE_CAPTION.get(rel)
    counter = {"n": 0}

    def add_caption(m: re.Match[str]) -> str:
        open_tag, rest = m.group(1), m.group(2)
        table = open_tag + rest
        if "<caption" in table:
            return table
        counter["n"] += 1
        if specific and counter["n"] == 1:
            text = specific
        else:
            text = "Data table"
        return open_tag + f"<caption>{text}</caption>" + rest

    html = re.sub(
        r"(<table\b[^>]*>)(.*?</table>)",
        add_caption,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(
        r"<th(?![^>]*scope=)",
        '<th scope="col"',
        html,
        flags=re.IGNORECASE,
    )
    return html


def mark_external_links(html: str) -> str:
    html = EXTERNAL_RE.sub("", html)
    html = PDF_RE.sub("", html)

    def one_link(m: re.Match[str]) -> str:
        start, href, mid, inner, end = (
            m.group(1),
            m.group(2),
            m.group(3),
            m.group(4),
            m.group(5),
        )
        if "skip-link" in start:
            return m.group(0)
        extra = ""
        if href.lower().endswith(".pdf"):
            extra += PDF
        if href.startswith(("http://", "https://")):
            if not any(host in href for host in INTERNAL_HOSTS):
                extra += EXTERNAL
        if extra and extra not in inner:
            inner = inner + extra
        return start + href + mid + inner + end

    return re.sub(
        r'(<a\b[^>]*?)(href="[^"]+")([^>]*>)(.*?)(</a>)',
        one_link,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def patch(path: Path, site_root: Path) -> bool:
    rel = page_key(path, site_root)
    html = path.read_text(encoding="utf-8")
    html = inject_skip_and_main(html)
    html = label_landmarks(html)
    html = mark_current_page(html, rel)
    html = caption_tables(html, rel)
    html = mark_external_links(html)
    html = EMPTY_SIDEBAR_A_RE.sub("", html)
    path.write_text(html, encoding="utf-8")
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
        if patch(path, site_root):
            count += 1
    print(f"Applied accessibility post-render fixes to {count} HTML page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
