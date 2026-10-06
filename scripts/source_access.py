#!/usr/bin/env python3
"""Decide which public-access links a source record may offer.

Front matter is the source of truth (`external_url`, `archived_url`,
`document_path`). Availability tokens keep the meanings in
docs/vocabularies.qmd: a publicly readable status must point at a real
copy, and a wanted or catalogue-only record must not grow a manufactured one.

Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from html import escape

# A visitor can open a copy. These tokens cannot publish without one.
PUBLIC_AVAILABILITY = frozenset({"full-text-public", "external-link-only"})

# docs/vocabularies.qmd — a typo must not slip past the public-copy check.
AVAILABILITY_TOKENS = frozenset(
    {
        "full-text-public",
        "external-link-only",
        "catalogue-or-citation-only",
        "known-to-exist-copy-sought",
        "physical-copy-known",
        "permission-required",
    }
)

# A file under documents/ is offered as a download only for these tokens.
# permission-required may name a file but must not offer it.
OFFER_DOCUMENT_AVAILABILITY = PUBLIC_AVAILABILITY

_SCALAR_FIELDS = (
    "availability",
    "external_url",
    "archived_url",
    "document_path",
    "example",
    "record_status",
)

_GOV_SUFFIXES = (
    "gov.bc.ca",
    "canada.ca",
    "gc.ca",
    "gg.ca",
    "leg.bc.ca",
    "bcombudsperson.ca",
    "seniorsadvocatebc.ca",
    "vch.ca",
)

_ARCHIVE_SUFFIXES = ("archive.org",)


@dataclass(frozen=True)
class SourceRecord:
    """Catalogue fields the access region and the validator both read."""

    path: Path
    availability: str
    external_url: str
    archived_url: str
    document_path: str
    example: bool
    record_status: str


@dataclass(frozen=True)
class AccessLink:
    """One visitor-facing link. `field` names the front-matter source."""

    field: str
    href: str
    label: str
    primary: bool


def parse_scalar_front_matter(text: str) -> dict[str, str] | None:
    """Return the scalar access fields, or None when the file has no front matter."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end_index = lines.index("---", 1)
    except ValueError:
        return None

    values: dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line or line[:1].isspace():
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key not in _SCALAR_FIELDS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value.strip()
    return values


def load_record(path: Path, root: Path) -> SourceRecord | None:
    """Load one source QMD. Index pages and files without front matter return None."""

    if path.name == "index.qmd":
        return None
    text = path.read_text(encoding="utf-8")
    fields = parse_scalar_front_matter(text)
    if fields is None:
        return None
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = path
    example_raw = fields.get("example", "").lower()
    return SourceRecord(
        path=Path(rel.as_posix()),
        availability=fields.get("availability", ""),
        external_url=fields.get("external_url", ""),
        archived_url=fields.get("archived_url", ""),
        document_path=fields.get("document_path", ""),
        example=example_raw in {"true", "yes"},
        record_status=fields.get("record_status", ""),
    )


def iter_source_records(root: Path) -> list[SourceRecord]:
    """Non-index source records, in filename order."""

    records: list[SourceRecord] = []
    for path in sorted((root / "sources").glob("*.qmd")):
        record = load_record(path, root)
        if record is not None:
            records.append(record)
    return records


def is_usable_http_url(value: str) -> bool:
    """True for an absolute http(s) URL with a host and no embedded whitespace."""

    value = value.strip()
    if not value or any(ch.isspace() for ch in value):
        return False
    if value.lower().startswith("javascript:"):
        return False
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"}:
        return False
    if not parts.hostname:
        return False
    return True


def normalize_url(value: str) -> str:
    """Compare locations, ignoring scheme/host case, a trailing slash, and fragments."""

    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _hostname(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_is(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)


def is_pdf_target(url: str) -> bool:
    path = urlsplit(url).path if "://" in url else url
    bare = path.split("?", 1)[0].split("#", 1)[0].lower()
    return bare.endswith(".pdf")


def resolve_document(root: Path, raw: str) -> tuple[Path | None, str | None]:
    """Resolve `document_path` to a file inside `documents/`.

    Returns `(path, None)` when the file exists, `(None, None)` when the field
    is empty, or `(None, message)` when the field is set but not a lawful
    hosted copy. `message` does not include the source filename.
    """

    raw = raw.strip()
    if not raw:
        return None, None
    if "://" in raw or raw.startswith("//"):
        return None, (
            f"document_path {raw!r} is a URL. Put web addresses in external_url "
            "or archived_url. document_path is only for a file hosted under documents/."
        )

    rel = raw[2:] if raw.startswith("./") else raw
    if rel.startswith("../documents/"):
        rel = rel[3:]
    parts = Path(rel).parts
    if rel.startswith(("/", "\\")) or ".." in parts:
        return None, (
            f"document_path {raw!r} escapes documents/. "
            "Hosted copies must stay inside documents/."
        )
    if not rel.startswith("documents/") or rel == "documents":
        return None, (
            f"document_path {raw!r} must be a path under documents/ "
            "(for example documents/1987-creekview-evaluation.pdf)."
        )

    docs_root = (root / "documents").resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(docs_root)
    except ValueError:
        return None, (
            f"document_path {raw!r} escapes documents/. "
            "Hosted copies must stay inside documents/."
        )
    if candidate.name.lower() == "readme.md":
        return None, (
            f"document_path {raw!r} points at documents/README.md, which is "
            "project documentation, not a hosted source."
        )
    if not candidate.is_file():
        return None, (
            f"document_path {raw!r} does not exist. A lawful hosted copy must be "
            "a real file under documents/. Do not point at a file that is not in the repository."
        )
    return candidate, None


def document_href(raw: str) -> str:
    """Visitor path from a page in `sources/` to a file under `documents/`."""

    rel = raw.strip()
    if rel.startswith("./"):
        rel = rel[2:]
    if rel.startswith("../documents/"):
        return rel
    return "../" + rel


def link_label(url: str, field: str, availability: str, *, archived_name_taken: bool) -> str:
    """Human-readable name. Never the raw URL, and never a generic 'click here'."""

    if field == "archived_url":
        if archived_name_taken:
            return "Additional archived copy"
        return "Archived copy"
    if field == "document_path":
        if is_pdf_target(url):
            return "Open the document (PDF)"
        return "Open the document"
    if availability == "catalogue-or-citation-only":
        return "Catalogue record"
    if availability in {"known-to-exist-copy-sought", "physical-copy-known"}:
        return "Related public page"
    if availability == "permission-required":
        return "Public page"

    host = _hostname(url)
    if any(_host_is(host, suffix) for suffix in _ARCHIVE_SUFFIXES):
        return "Archived copy"
    if is_pdf_target(url):
        path = (urlsplit(url).path if "://" in url else url).lower()
        if availability == "full-text-public" or re.search(r"report", path):
            return "Full report (PDF)"
        return "Open the document (PDF)"
    if any(_host_is(host, suffix) for suffix in _GOV_SUFFIXES):
        return "Government page"
    return "Read the source"


def plan_links(record: SourceRecord, root: Path) -> list[AccessLink]:
    """Links to render, primary first. Empty when the record offers no copy."""

    planned: list[tuple[str, str]] = []
    external = record.external_url.strip()
    archived = record.archived_url.strip()
    if is_usable_http_url(external):
        planned.append(("external_url", external))
    if is_usable_http_url(archived) and (
        not is_usable_http_url(external) or normalize_url(archived) != normalize_url(external)
    ):
        planned.append(("archived_url", archived))

    if record.availability in OFFER_DOCUMENT_AVAILABILITY:
        resolved, error = resolve_document(root, record.document_path)
        if resolved is not None and error is None:
            planned.append(("document_path", document_href(record.document_path)))

    archived_name_taken = False
    links: list[AccessLink] = []
    for index, (field, href) in enumerate(planned):
        label = link_label(
            href,
            field,
            record.availability,
            archived_name_taken=archived_name_taken,
        )
        if label == "Archived copy":
            archived_name_taken = True
        links.append(AccessLink(field=field, href=href, label=label, primary=index == 0))
    return links


def validate_record(record: SourceRecord, root: Path) -> list[str]:
    """Return human-readable failures. An empty list means the record may publish."""

    rel = record.path.as_posix()
    errors: list[str] = []

    if record.availability not in AVAILABILITY_TOKENS:
        shown = record.availability or "(empty)"
        allowed = ", ".join(sorted(AVAILABILITY_TOKENS))
        errors.append(
            f"{rel}: availability {shown!r} is not a controlled token. "
            f"Use one of: {allowed}. See docs/vocabularies.qmd."
        )

    for field, value in (
        ("external_url", record.external_url),
        ("archived_url", record.archived_url),
    ):
        if value.strip() and not is_usable_http_url(value):
            errors.append(
                f"{rel}: {field} is not a usable http(s) URL ({value.strip()!r}). "
                "Use an absolute http:// or https:// address, or leave the field empty."
            )

    document_ok = False
    if record.document_path.strip():
        resolved, message = resolve_document(root, record.document_path)
        if message:
            errors.append(f"{rel}: {message}")
        else:
            document_ok = resolved is not None
        if record.availability not in OFFER_DOCUMENT_AVAILABILITY | {"permission-required"}:
            errors.append(
                f"{rel}: document_path is set, but availability is {record.availability or '(empty)'}. "
                "Host a file only when availability is full-text-public or external-link-only "
                "(visitors may open it) or permission-required (the page must not offer a download). "
                "Do not attach a file to a wanted, catalogue-only, or physical-copy record."
            )

    if record.availability in PUBLIC_AVAILABILITY:
        has_url = is_usable_http_url(record.external_url) or is_usable_http_url(
            record.archived_url
        )
        if not has_url and not document_ok:
            errors.append(
                f"{rel}: availability is {record.availability}, which requires a public copy, "
                "but external_url, archived_url, and document_path do not provide one. "
                "Add a usable external_url or archived_url, or a lawful document_path to an "
                "existing file under documents/. If no public copy has been recovered, change "
                "availability instead of inventing a link. "
                "See docs/vocabularies.qmd and docs/evidence-status.qmd."
            )
    return errors


def render_access_panel(links: list[AccessLink]) -> str:
    """HTML for the Open this source region. Empty when there is nothing to offer."""

    if not links:
        return ""
    items: list[str] = []
    for link in links:
        classes = "source-access-link"
        if link.primary:
            classes += " source-access-link-primary"
        items.append(
            f'<li><a class="{classes}" href="{escape(link.href, quote=True)}">{escape(link.label)}</a></li>'
        )
    body = "\n".join(items)
    return (
        '<div class="source-access" role="region" aria-labelledby="source-access-title">\n'
        '<h2 id="source-access-title" class="source-access-title">Open this source</h2>\n'
        '<ul class="source-access-links">\n'
        f"{body}\n"
        "</ul>\n"
        "</div>\n"
    )


_IDENT_SECTION_RE = re.compile(
    r"<section\b[^>]*\bid=[\"']identification[\"']",
    flags=re.IGNORECASE,
)
_IDENT_HEADING_RE = re.compile(
    r"<h2\b[^>]*\bid=[\"']identification[\"']",
    flags=re.IGNORECASE,
)
_LEVEL2_SECTION_RE = re.compile(
    r"<section\b[^>]*\bclass=[\"'][^\"']*\blevel2\b",
    flags=re.IGNORECASE,
)
_H2_RE = re.compile(r"<h2\b", flags=re.IGNORECASE)


def insert_access_panel(html: str, panel: str) -> str:
    """Place the region after leading callouts and before Identification."""

    if not panel or 'class="source-access"' in html:
        return html
    for pattern in (_IDENT_SECTION_RE, _IDENT_HEADING_RE, _LEVEL2_SECTION_RE, _H2_RE):
        match = pattern.search(html)
        if match:
            return html[: match.start()] + panel + html[match.start() :]
    return html


def access_panel_html(raw: str) -> str:
    """Return the rendered region, or '' when the page has none.

    The region has no nested divs, so the first closing tag is the boundary.
    """

    match = re.search(
        r'<div class="source-access"[^>]*>.*?</div>',
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(0) if match else ""
