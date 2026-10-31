"""Regression checks for TED WAF responses that look like documents."""
import unittest
from unittest.mock import patch
from src import document_parser
from src.ted_xml_enricher import _failure_category


class FakeResponse:
    def __init__(self, status, headers, body=b""):
        self.status = status
        self.headers = headers
        self.body = body

    def geturl(self):
        return "https://ted.europa.eu/en/notice/756345-2026/xml"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.body[:size]


class FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout=None):
        return self.response


class TedWafChallengeTests(unittest.TestCase):
    URL = "https://ted.europa.eu/en/notice/756345-2026/xml"

    def fetch(self, status, headers, body=b""):
        with patch.object(document_parser, "_public_http_url", return_value=True), patch.object(
            document_parser.urllib.request, "build_opener",
            return_value=FakeOpener(FakeResponse(status, headers, body))
        ):
            return document_parser._download(self.URL)

    def test_empty_202_challenge_rejected(self):
        with self.assertRaisesRegex(ValueError, "^ted_waf_challenge$"):
            self.fetch(202, {"Content-Type": "text/html", "x-amzn-waf-action": "challenge"})

    def test_202_without_header_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "^ted_waf_challenge$"):
            self.fetch(202, {"Content-Type": "text/html"})

    def test_waf_header_on_200_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "^ted_waf_challenge$"):
            self.fetch(200, {"Content-Type": "text/html", "x-amzn-waf-action": "challenge"}, b"<html>challenge</html>")

    def test_normal_200_xml_keeps_existing_download_contract(self):
        body = b"<?xml version='1.0'?><test/>"
        self.assertEqual(
            self.fetch(200, {"Content-Type": "application/xml"}, body),
            (body, "application/xml", self.URL),
        )

    def test_safe_aggregate_category(self):
        self.assertEqual(
            _failure_category({"error": "ValueError:ted_waf_challenge"}),
            "ted_waf_challenge",
        )


if __name__ == "__main__":
    unittest.main()
