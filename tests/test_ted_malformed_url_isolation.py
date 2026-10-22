"""Malformed source URLs must not prevent later TED notice discovery."""

import unittest
from unittest.mock import patch

from src import ted_xml_enricher


class TedMalformedUrlsTests(unittest.TestCase):
    def test_invalid_ipv6_preceding_valid_ted_xml_is_skipped(self):
        item = {"source": "TED", "official_links": [
            "https://[broken/notice/123-2026/xml",
            "https://ted.europa.eu/en/notice/123-2026/xml",
        ]}
        self.assertEqual(ted_xml_enricher._ted_xml_url(item),
                         "https://ted.europa.eu/en/notice/123-2026/xml")

    def test_invalid_ipv6_preceding_ted_notice_fallback_is_skipped(self):
        item = {"source": "TED", "official_links": [
            "https://[broken/notice/123-2026",
            "https://ted.europa.eu/en/notice/123-2026",
        ]}
        self.assertEqual(ted_xml_enricher._ted_xml_url(item),
                         "https://ted.europa.eu/en/notice/123-2026/xml")

    def test_bad_notice_does_not_abort_candidate_selection(self):
        items = [
            {"source": "OTHER", "source_url": "https://[broken/url"},
            {"source": "TED", "source_url": "https://ted.europa.eu/en/notice/123-2026"},
        ]
        with patch.object(ted_xml_enricher, "enrich_opportunity", return_value=False) as reader:
            out = ted_xml_enricher.enrich_payload({"opportunities": items})
        self.assertEqual(out["document_extraction"]["ted_xml_attempted"], 1)
        reader.assert_called_once_with(items[1])


if __name__ == "__main__":
    unittest.main()
