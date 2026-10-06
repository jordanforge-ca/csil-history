#!/usr/bin/env python3
"""Tests for public source-access planning and validation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import check_source_access
import post_render
import source_access

ROOT = Path(__file__).resolve().parents[1]


def _write_source(root: Path, name: str, **fields: str) -> None:
    sources = root / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    lines = ["---", "title: \"Fixture\""]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines.extend(["---", "", "Body", ""])
    (sources / name).write_text("\n".join(lines), encoding="utf-8")


class SourceAccessTests(unittest.TestCase):
    def test_repository_catalogue_passes(self) -> None:
        errors = check_source_access.check_root(ROOT)
        self.assertEqual(errors, [])
        public = source_access.PUBLIC_AVAILABILITY
        for record in source_access.iter_source_records(ROOT):
            links = source_access.plan_links(record, ROOT)
            if record.availability in public:
                self.assertTrue(links, record.path.as_posix())
            for link in links:
                self.assertNotIn("http://", link.label.lower())
                self.assertNotIn("https://", link.label.lower())
                self.assertNotEqual(link.label.strip().lower(), "open source")
                self.assertNotIn(link.label.lower(), {"click here", "here", "link", "read more"})

    def test_public_pdf_report_label(self) -> None:
        record = source_access.load_record(
            ROOT / "sources/2017-seniors-advocate-caregivers-distress.qmd",
            ROOT,
        )
        assert record is not None
        links = source_access.plan_links(record, ROOT)
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].primary)
        self.assertEqual(links[0].field, "external_url")
        self.assertEqual(links[0].label, "Full report (PDF)")
        self.assertTrue(links[0].href.endswith(".pdf"))

    def test_government_page_and_distinct_archive(self) -> None:
        record = source_access.load_record(
            ROOT / "sources/2015-bc-csil-rate-schedule.qmd",
            ROOT,
        )
        assert record is not None
        links = source_access.plan_links(record, ROOT)
        self.assertEqual([link.label for link in links], ["Government page", "Archived copy"])
        self.assertNotEqual(links[0].href, links[1].href)
        self.assertTrue(links[0].primary)
        self.assertFalse(links[1].primary)

    def test_duplicate_archive_url_is_one_link(self) -> None:
        record = source_access.load_record(
            ROOT / "sources/2008-program-review-synthesis.qmd",
            ROOT,
        )
        assert record is not None
        links = source_access.plan_links(record, ROOT)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].label, "Archived copy")
        self.assertIn("archive.org", links[0].href)

    def test_catalogue_record_is_not_labelled_as_the_full_text(self) -> None:
        record = source_access.load_record(
            ROOT / "sources/1987-mattinson-rompf-creekview.qmd",
            ROOT,
        )
        assert record is not None
        links = source_access.plan_links(record, ROOT)
        self.assertEqual([link.label for link in links], ["Catalogue record"])
        self.assertIn("pubmed.ncbi.nlm.nih.gov", links[0].href)

    def test_wanted_and_template_offer_no_link(self) -> None:
        for name in (
            "wanted-creekview-202-evaluation.qmd",
            "wanted-ministry-csil-pilot-records.qmd",
            "example-template-source-record.qmd",
        ):
            record = source_access.load_record(ROOT / "sources" / name, ROOT)
            assert record is not None
            self.assertEqual(source_access.plan_links(record, ROOT), [])
            self.assertEqual(source_access.validate_record(record, ROOT), [])

    def test_policy_pdf_is_a_document_not_a_report(self) -> None:
        record = source_access.load_record(ROOT / "sources/hcc-policy-manual-4c.qmd", ROOT)
        assert record is not None
        links = source_access.plan_links(record, ROOT)
        self.assertEqual(links[0].label, "Open the document (PDF)")

    def test_ombudsperson_pdf_is_a_full_report(self) -> None:
        record = source_access.load_record(
            ROOT / "sources/2012-ombudsperson-best-of-care.qmd",
            ROOT,
        )
        assert record is not None
        self.assertEqual(source_access.plan_links(record, ROOT)[0].label, "Full report (PDF)")

    def test_news_article_is_read_the_source(self) -> None:
        record = source_access.load_record(
            ROOT / "sources/2018-vancouversun-walt-lawrence.qmd",
            ROOT,
        )
        assert record is not None
        self.assertEqual(source_access.plan_links(record, ROOT)[0].label, "Read the source")

    def test_panel_is_inserted_before_identification(self) -> None:
        panel = source_access.render_access_panel(
            [
                source_access.AccessLink(
                    "external_url",
                    "https://example.com/report.pdf",
                    "Full report (PDF)",
                    True,
                )
            ]
        )
        html = (
            '<div class="callout">Inspected</div>\n'
            '<section class="level2" id="identification"><h2>Identification</h2></section>'
        )
        out = source_access.insert_access_panel(html, panel)
        self.assertLess(out.index("source-access"), out.index('id="identification"'))
        self.assertIn("<h2 id=\"source-access-title\"", out)
        self.assertIn("Full report (PDF)", out)
        self.assertNotIn("<strong>", out)

    def test_public_availability_without_a_copy_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_source(
                root,
                "missing.qmd",
                availability="full-text-public",
                external_url='""',
                archived_url='""',
                document_path='""',
            )
            errors = check_source_access.check_root(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("sources/missing.qmd", errors[0])
        self.assertIn("full-text-public", errors[0])
        self.assertIn("external_url", errors[0])

    def test_unusable_url_fails_even_when_another_copy_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_source(
                root,
                "bad-url.qmd",
                availability="external-link-only",
                external_url='"not a url"',
                archived_url='"https://example.com/copy"',
            )
            errors = check_source_access.check_root(root)
        self.assertTrue(any("external_url is not a usable http(s) URL" in error for error in errors))

    def test_archived_url_alone_satisfies_external_link_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_source(
                root,
                "archive-only.qmd",
                availability="external-link-only",
                archived_url='"https://archive.org/details/example"',
            )
            record = source_access.load_record(root / "sources/archive-only.qmd", root)
            assert record is not None
            self.assertEqual(source_access.validate_record(record, root), [])
            links = source_access.plan_links(record, root)
            self.assertEqual(links[0].label, "Archived copy")

    def test_hosted_file_satisfies_full_text_public(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "documents").mkdir()
            (root / "documents" / "report.pdf").write_bytes(b"%PDF-1.4")
            _write_source(
                root,
                "hosted.qmd",
                availability="full-text-public",
                document_path='"documents/report.pdf"',
            )
            record = source_access.load_record(root / "sources/hosted.qmd", root)
            assert record is not None
            self.assertEqual(source_access.validate_record(record, root), [])
            links = source_access.plan_links(record, root)
            self.assertEqual(links[0].label, "Open the document (PDF)")
            self.assertEqual(links[0].href, "../documents/report.pdf")

    def test_missing_and_escaping_document_paths_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "documents").mkdir()
            _write_source(
                root,
                "gone.qmd",
                availability="full-text-public",
                document_path='"documents/missing.pdf"',
            )
            _write_source(
                root,
                "escape.qmd",
                availability="full-text-public",
                document_path='"documents/../../etc/passwd"',
            )
            errors = check_source_access.check_root(root)
        joined = "\n".join(errors)
        self.assertIn("documents/missing.pdf", joined)
        self.assertIn("does not exist", joined)
        self.assertIn("escapes documents/", joined)

    def test_permission_required_does_not_offer_a_download(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "documents").mkdir()
            (root / "documents" / "private.pdf").write_bytes(b"%PDF-1.4")
            _write_source(
                root,
                "private.qmd",
                availability="permission-required",
                document_path='"documents/private.pdf"',
            )
            record = source_access.load_record(root / "sources/private.qmd", root)
            assert record is not None
            self.assertEqual(source_access.validate_record(record, root), [])
            self.assertEqual(source_access.plan_links(record, root), [])

    def test_wanted_record_rejects_a_hosted_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "documents").mkdir()
            (root / "documents" / "found.pdf").write_bytes(b"%PDF-1.4")
            _write_source(
                root,
                "wanted.qmd",
                availability="known-to-exist-copy-sought",
                document_path='"documents/found.pdf"',
            )
            errors = check_source_access.check_root(root)
        self.assertTrue(any("known-to-exist-copy-sought" in error for error in errors))

    def test_unknown_availability_token_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_source(root, "typo.qmd", availability="fulltext-public")
            errors = check_source_access.check_root(root)
        self.assertTrue(any("not a controlled token" in error for error in errors))

    def test_same_url_with_trailing_slash_is_not_repeated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_source(
                root,
                "same.qmd",
                availability="external-link-only",
                external_url='"https://archive.org/details/example/"',
                archived_url='"https://archive.org/details/example"',
            )
            record = source_access.load_record(root / "sources/same.qmd", root)
            assert record is not None
            self.assertEqual(len(source_access.plan_links(record, root)), 1)

    def test_pdf_suffix_is_not_repeated_when_the_label_already_says_pdf(self) -> None:
        labelled = post_render.mark_external_links(
            '<a href="https://example.com/report.pdf">Full report (PDF)</a>'
        )
        self.assertEqual(labelled.lower().count("(pdf)"), 1)
        self.assertIn("(external site)", labelled)

        plain = post_render.mark_external_links(
            '<a href="https://example.com/report.pdf">Read the report</a>'
        )
        self.assertIn("(PDF)", plain)
        self.assertIn("(external site)", plain)

    def test_injects_real_catalogue_page_before_identification(self) -> None:
        html = (
            "<main><h1>Caregivers</h1>"
            '<div class="callout">Source inspected</div>'
            '<section id="identification" class="level2"><h2>Identification</h2></section>'
            "</main>"
        )
        out = post_render.inject_source_access(
            html,
            "sources/2017-seniors-advocate-caregivers-distress.html",
            repo_root=ROOT,
        )
        panel = source_access.access_panel_html(out)
        self.assertIn("Full report (PDF)", panel)
        self.assertIn("seniorsadvocatebc.ca", panel)
        self.assertLess(out.index("Open this source"), out.index('id="identification"'))
        self.assertNotIn("Open source", panel)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SourceAccessTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
