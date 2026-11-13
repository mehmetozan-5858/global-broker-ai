"""TED notice downloads must never accept generic or unrelated redirects."""
import unittest
from src.ted_xml_enricher import _verify_ted_redirect


class TEDRedirectIdentityTests(unittest.TestCase):
    START = "https://ted.europa.eu/en/notice/681487-2026/xml"

    def test_redirect_to_generic_ted_home_rejected(self):
        with self.assertRaisesRegex(ValueError, "ted_document_notice_redirect_mismatch"):
            _verify_ted_redirect(self.START, "https://ted.europa.eu/en")

    def test_redirect_to_other_notice_rejected(self):
        with self.assertRaisesRegex(ValueError, "ted_document_notice_redirect_mismatch"):
            _verify_ted_redirect(self.START, "https://ted.europa.eu/en/notice/681488-2026/xml")

    def test_same_notice_redirect_allowed(self):
        _verify_ted_redirect(self.START, "https://ted.europa.eu/en/notice/681487-2026/html")

    def test_offsite_redirect_rejected(self):
        with self.assertRaisesRegex(ValueError, "ted_document_origin_changed"):
            _verify_ted_redirect(self.START, "https://example.org/en/notice/681487-2026/xml")


if __name__ == "__main__":
    unittest.main()
