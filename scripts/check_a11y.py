#!/usr/bin/env python3
"""First-pass accessibility checks on rendered Quarto HTML.

Standard library only. Not a WCAG audit and not a browser-based axe run.
"""

from __future__ import annotations

import html as html_lib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

GENERIC_LINK_TEXT = {
    "click here",
    "here",
    "read more",
    "more",
    "link",
    "this",
    "this page",
    "this link",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: str | None = None
        self.title_parts: list[str] = []
        self.in_title = False
        self.in_svg = False
        self.headings: list[tuple[int, str]] = []
        self.heading_buf: list[str] = []
        self.heading_level: int | None = None
        self.images: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.link_buf: list[str] = []
        self.in_link = False
        self.link_href: str | None = None
        self.link_label: str | None = None
        self.link_role: str | None = None
        self.has_skip_link = False
        self.has_main = False
        self.has_doc_content_id = False
        self.positive_tabindexes: list[str] = []
        self._current_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v for k, v in attrs}
        if tag == "html":
            self.html_lang = attr.get("lang")
        if tag == "title":
            self.in_title = True
        if tag == "svg":
            self.in_svg = True
        if tag == "main":
            self.has_main = True
        element_id = attr.get("id") or ""
        if element_id == "quarto-document-content":
            self.has_doc_content_id = True
            if tag != "main":
                # Quarto uses a content container; treat it as the main target.
                self.has_main = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_level = int(tag[1])
            self.heading_buf = []
        if tag == "img":
            self.images.append({"src": attr.get("src"), "alt": attr.get("alt")})
        if tag == "a":
            self.in_link = True
            self.link_href = attr.get("href")
            self.link_label = attr.get("aria-label")
            self.link_role = attr.get("role")
            self.link_buf = []
            classes = (attr.get("class") or "").split()
            if "skip-link" in classes:
                self.has_skip_link = True
        tabindex = attr.get("tabindex")
        if tabindex is not None:
            try:
                if int(tabindex) > 0:
                    self.positive_tabindexes.append(tabindex)
            except ValueError:
                self.positive_tabindexes.append(tabindex)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag == "svg":
            self.in_svg = False
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self.heading_level:
            text = _norm("".join(self.heading_buf))
            self.headings.append((self.heading_level, text))
            self.heading_level = None
            self.heading_buf = []
        if tag == "a" and self.in_link:
            text = _norm("".join(self.link_buf))
            self.links.append(
                {
                    "href": self.link_href,
                    "text": text,
                    "aria_label": self.link_label,
                    "role": self.link_role,
                }
            )
            self.in_link = False
            self.link_href = None
            self.link_label = None
            self.link_role = None
            self.link_buf = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.heading_level is not None:
            self.heading_buf.append(data)
        if self.in_link and not self.in_svg:
            self.link_buf.append(data)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def check_page(path: Path, site_root: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = PageParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:  # noqa: BLE001 — report parse problems as a11y failures
        return [f"{path}: HTML parse error: {exc}"]

    rel = path.relative_to(site_root)
    errors: list[str] = []
    title = _norm("".join(parser.title_parts))

    if not parser.html_lang:
        errors.append(f"{rel}: <html> is missing a lang attribute")
    if not title:
        errors.append(f"{rel}: missing or empty <title>")

    h1s = [h for h in parser.headings if h[0] == 1]
    if not h1s:
        errors.append(f"{rel}: no h1 heading")
    elif len(h1s) > 1:
        errors.append(f"{rel}: multiple h1 headings ({len(h1s)})")

    last_level = 0
    for level, text in parser.headings:
        if last_level and level > last_level + 1:
            errors.append(
                f"{rel}: heading level skips from h{last_level} to h{level} ({text or 'untitled'})"
            )
        last_level = level

    if not parser.has_skip_link:
        errors.append(f"{rel}: missing skip-to-content link")
    if not parser.has_main and not parser.has_doc_content_id:
        errors.append(f"{rel}: missing main landmark or #quarto-document-content")

    for image in parser.images:
        if image["alt"] is None:
            errors.append(f"{rel}: image missing alt attribute ({image['src']})")

    for link in parser.links:
        href = (link["href"] or "").strip()
        text = (link["text"] or "").strip()
        if href.startswith("#") and href not in {"#", "#quarto-document-content"}:
            pass
        if not href:
            # Quarto sidebar collapse uses <a role="navigation" aria-label=...>
            # without href. Accept only if an accessible name is present.
            if (link.get("aria_label") or "").strip():
                continue
            errors.append(f"{rel}: anchor tag without href")
            continue
        if href.startswith("javascript:"):
            errors.append(f"{rel}: javascript: link")
        visible = text.lower()
        if not visible and not href.startswith("#"):
            # Icon-only or aria-only controls still need accessible names.
            # Quarto search/navbar may use aria-label; allow hash and empty logo skips
            # only when classed skip-link already handled.
            if href not in {"#quarto-document-content"}:
                errors.append(f"{rel}: empty link text (href={href})")
        elif visible in GENERIC_LINK_TEXT:
            errors.append(f"{rel}: non-descriptive link text “{text}” (href={href})")

    if parser.positive_tabindexes:
        errors.append(
            f"{rel}: positive tabindex values break focus order ({', '.join(parser.positive_tabindexes)})"
        )

    return errors


def iter_html(site_root: Path) -> list[Path]:
    skip_dirs = {"site_libs"}
    files: list[Path] = []
    for path in site_root.rglob("*.html"):
        if any(part in skip_dirs for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main(argv: list[str]) -> int:
    site_root = Path(argv[1] if len(argv) > 1 else "_site").resolve()
    if not site_root.is_dir():
        print(f"Site directory not found: {site_root}", file=sys.stderr)
        return 2

    pages = iter_html(site_root)
    if not pages:
        print(f"No HTML pages found under {site_root}", file=sys.stderr)
        return 2

    errors: list[str] = []
    for page in pages:
        errors.extend(check_page(page, site_root))

    if errors:
        print(f"Accessibility check failed ({len(errors)} issue(s)):\n")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Accessibility check passed for {len(pages)} HTML page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
