"""Bounded TED download behavior regression coverage."""
import unittest
from unittest.mock import patch
import urllib.error
from src import ted_xml_enricher as ted


class TedDownloadPolicyTests(unittest.TestCase):
    def setUp(self):
        ted._TED_NEXT_REQUEST = 0.0

    def test_api_multilingual_xml_link_is_preferred(self):
        item = {"source": "TED", "publication-number": "756345-2026",
                "links": {"xml": {"MUL": "https://ted.europa.eu/en/notice/756345-2026/xml"}}}
        self.assertEqual(ted._ted_xml_url(item), item["links"]["xml"]["MUL"])

    def test_cross_notice_or_foreign_api_url_is_rejected(self):
        for url in ("https://evil.example/en/notice/756345-2026/xml",
                    "https://ted.europa.eu/en/notice/111111-2026/xml"):
            item = {"source": "TED", "publication-number": "756345-2026",
                    "links": {"xml": {"MUL": url}}}
            self.assertEqual(ted._ted_xml_url(item),
                             "https://ted.europa.eu/en/notice/756345-2026/xml")

    def test_rate_limit_retries_then_succeeds(self):
        error = urllib.error.HTTPError("https://ted.europa.eu/", 429, "Too Many Requests",
                                      {"Retry-After": "2"}, None)
        with patch.object(ted.document_parser, "_download", side_effect=[error, (b"<x/>", "application/xml", "ok")]) as download, \
             patch.object(ted.time, "sleep"), patch.object(ted.time, "monotonic", side_effect=[0, 0, 0, 0, 0, 0]):
            result = ted._download_ted("https://ted.europa.eu/en/notice/756345-2026/xml", 2048)
        self.assertEqual(result[0], b"<x/>")
        self.assertEqual(download.call_count, 2)

    def test_retries_are_bounded(self):
        error = urllib.error.HTTPError("https://ted.europa.eu/", 429, "Too Many Requests",
                                      {"Retry-After": "99999"}, None)
        with patch.object(ted.document_parser, "_download", side_effect=error) as download, \
             patch.object(ted.time, "sleep"), patch.object(ted.time, "monotonic", return_value=0):
            with self.assertRaises(urllib.error.HTTPError):
                ted._download_ted("https://ted.europa.eu/en/notice/756345-2026/xml", 2048)
        self.assertEqual(download.call_count, 3)

    def test_no_html_fallback(self):
        with patch.object(ted, "_download_ted", return_value=(b"%PDF", "application/pdf", "https://ted.europa.eu/en/notice/756345-2026/pdf")) as download, \
             patch.object(ted.document_parser, "_parse_pdf", return_value="756345-2026 " + "a" * 170):
            ted._fallback_document("https://ted.europa.eu/en/notice/756345-2026/xml",
                                   {"source": "TED", "notice_context": {"call_for_tenders": True}}, [])
            self.assertTrue(all("/html" not in call.args[0] for call in download.call_args_list))


if __name__ == "__main__":
    unittest.main()
