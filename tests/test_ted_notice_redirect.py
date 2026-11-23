import unittest

from src.ted_xml_enricher import _verify_ted_redirect


class TedNoticeRedirectTests(unittest.TestCase):
    def test_matching_notice_redirect_allowed(self):
        _verify_ted_redirect(
            "https://ted.europa.eu/en/notice/775258-2026/xml",
            "https://ted.europa.eu/en/notice/775258-2026/xml",
        )
        _verify_ted_redirect(
            "https://ted.europa.eu/en/notice/775258-2026/xml",
            "https://ted.europa.eu/en/notice/-/detail/775258-2026",
        )

    def test_mismatched_or_missing_notice_redirect_rejected(self):
        request = "https://ted.europa.eu/en/notice/775258-2026/xml"
        for redirect in [
            "https://ted.europa.eu/en/",
            "https://ted.europa.eu/en/notice",
            "https://ted.europa.eu/en/notice/775259-2026/xml",
        ]:
            with self.subTest(redirect=redirect):
                with self.assertRaisesRegex(ValueError, "ted_document_notice_redirect_mismatch"):
                    _verify_ted_redirect(request, redirect)

    def test_official_host_lookalike_and_credential_redirect_rejected(self):
        request = "https://ted.europa.eu/en/notice/775258-2026/xml"
        for redirect in [
            "http://ted.europa.eu/en/notice/775258-2026/xml",
            "https://ted.europa.eu.evil.test/en/notice/775258-2026/xml",
            "https://user@ted.europa.eu/en/notice/775258-2026/xml",
            "https://ted.europa.eu:444/en/notice/775258-2026/xml",
        ]:
            with self.subTest(redirect=redirect):
                with self.assertRaisesRegex(ValueError, "ted_document_origin_changed"):
                    _verify_ted_redirect(request, redirect)


if __name__ == "__main__":
    unittest.main()
