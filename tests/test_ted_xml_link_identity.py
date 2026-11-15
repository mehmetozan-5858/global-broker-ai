"""TED explicit XML links must be tied to the notice identity."""
import unittest
from src.ted_xml_enricher import _ted_xml_url


class TEDXMLLinkIdentityTests(unittest.TestCase):
    def test_generic_xml_link_rejected(self):
        item = {"source": "OTHER", "document_url": "https://ted.europa.eu/en/xml"}
        self.assertIsNone(_ted_xml_url(item))

    def test_different_notice_link_rejected(self):
        item = {"source": "OTHER", "publication-number": "681487-2026",
                "document_url": "https://ted.europa.eu/en/notice/681488-2026/xml"}
        self.assertIsNone(_ted_xml_url(item))

    def test_matching_notice_link_accepted(self):
        item = {"source": "TED", "publication-number": "681487-2026",
                "document_url": "https://ted.europa.eu/en/notice/681487-2026/xml"}
        self.assertEqual(_ted_xml_url(item), item["document_url"])

    def test_non_ted_xml_link_not_used_as_ted(self):
        item = {"source": "OTHER", "document_url": "https://example.org/notice/681487-2026.xml"}
        self.assertIsNone(_ted_xml_url(item))


if __name__ == "__main__":
    unittest.main()
