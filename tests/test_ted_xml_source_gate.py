"""TED document source classification must reject non-XML responses."""
import unittest
from src.ted_xml_parser import is_xml_source


class TEDXMLSourceGateTests(unittest.TestCase):
    URL = "https://ted.europa.eu/en/notice/681487-2026/xml"

    def test_json_response_at_xml_url_is_not_xml(self):
        self.assertFalse(is_xml_source(b'{"error":"rate limit"}', "application/json", self.URL))

    def test_plain_text_response_at_xml_url_is_not_xml(self):
        self.assertFalse(is_xml_source(b"temporarily unavailable", "text/plain", self.URL))

    def test_html_response_at_xml_url_is_not_xml(self):
        self.assertFalse(is_xml_source(b"<html><body>Loading...</body></html>", "text/html", self.URL))

    def test_real_xml_header_is_allowed(self):
        self.assertTrue(is_xml_source(b'<?xml version="1.0"?><Notice>Official</Notice>', "application/xml", self.URL))


if __name__ == "__main__":
    unittest.main()
