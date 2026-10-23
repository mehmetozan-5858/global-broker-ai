"""Prevent cross-notice TED redirects from contaminating a customer dossier."""

import unittest
from unittest.mock import patch

from src import document_parser, ted_xml_enricher

PUBLICATION = "123456-2026"
OTHER = "999999-2026"
XML_URL = f"https://ted.europa.eu/en/notice/{PUBLICATION}/xml"
TEXT = PUBLICATION + " Procurement requirements. " * 20
XML = ("<?xml version='1.0'?><notice><description>" + TEXT + "</description></notice>").encode()


class TedRedirectIdentityTests(unittest.TestCase):
    def test_xml_redirect_to_other_notice_is_not_accepted(self):
        def download(url, *args):
            if url.endswith("/xml"):
                return XML, "application/xml", f"https://ted.europa.eu/en/notice/{OTHER}/xml"
            raise ValueError("fallback_unavailable")
        row = {"source": "TED", "publication-number": PUBLICATION}
        with patch.object(document_parser, "_download", side_effect=download):
            self.assertFalse(ted_xml_enricher.enrich_opportunity(row))
        self.assertNotIn("document_extracted_text", row)
        self.assertFalse(row["document_extraction"]["ted_xml_parsed"])
        self.assertTrue(any("ted_document_notice_redirect_mismatch" in a.get("error", "")
                            for a in row["document_extraction"]["attempts"]))

    def test_html_redirect_to_other_notice_is_not_accepted_even_if_text_mentions_requested_id(self):
        def download(url, *args):
            if url.endswith("/html"):
                return b"<html>source</html>", "text/html", f"https://ted.europa.eu/en/notice/-/detail/{OTHER}"
            raise ValueError("xml_unavailable")
        row = {"source": "TED", "publication-number": PUBLICATION, "form-type": "result"}
        with patch.object(document_parser, "_download", side_effect=download), patch.object(
            document_parser, "_parse_html_page", return_value=(TEXT, [])
        ) as parser:
            self.assertFalse(ted_xml_enricher.enrich_opportunity(row))
        parser.assert_not_called()
        self.assertNotIn("document_extracted_text", row)

    def test_xml_offsite_redirect_is_not_accepted(self):
        row = {"source": "TED", "publication-number": PUBLICATION}
        with patch.object(document_parser, "_download", side_effect=[
            (XML, "application/xml", "https://other.example/notice/" + PUBLICATION + "/xml"),
            ValueError("html_unavailable"),
        ]):
            self.assertFalse(ted_xml_enricher.enrich_opportunity(row))
        self.assertNotIn("document_extracted_text", row)

    def test_mismatched_explicit_link_is_skipped_for_canonical_notice(self):
        row = {
            "source": "TED", "publication-number": PUBLICATION,
            "official_links": [f"https://ted.europa.eu/en/notice/{OTHER}/xml"],
        }
        self.assertEqual(ted_xml_enricher._ted_xml_url(row), XML_URL)

    def test_same_notice_redirect_is_allowed(self):
        row = {"source": "TED", "publication-number": PUBLICATION}
        with patch.object(document_parser, "_download", return_value=(
            XML, "application/xml", f"https://ted.europa.eu/en/notice/-/detail/{PUBLICATION}/xml"
        )):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(row))
        self.assertTrue(row["document_extraction"]["ted_xml_parsed"])


if __name__ == "__main__":
    unittest.main()
