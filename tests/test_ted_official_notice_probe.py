import unittest
from unittest.mock import patch

from src.ted_official_notice_probe import inspect_notice, safe_error_code


class OfficialTedProbeTests(unittest.TestCase):
    URL = "https://ted.europa.eu/en/notice/775258-2026/xml"

    def test_readonly_probe_reports_identity_digest_without_claiming_annex(self):
        xml = (b"<?xml version='1.0'?><Notice><Publication>775258-2026</Publication>"
               b"<Description>Verified technical scope placeholder</Description></Notice>")
        with patch("src.ted_official_notice_probe.parse_ted_xml",
                   return_value=("x" * 200, [])), patch(
                   "src.ted_official_notice_probe.extract_ted_lots",
                   return_value=[{"lot_id": "LOT-0001"}]):
            result = inspect_notice("775258-2026",
                fetcher=lambda url: (xml, "application/xml", url))
        self.assertTrue(result["notice_identity_found"])
        self.assertTrue(result["xml_readable"])
        self.assertEqual(result["structured_lot_count"], 1)
        self.assertEqual(len(result["sha256"]), 64)
        self.assertFalse(result["annex_completeness_verified"])
        self.assertFalse(result["commercial_acceptance"])
        self.assertNotIn("Verified technical scope", str(result))

    def test_wrong_notice_identity_fails_closed(self):
        xml = b"<?xml version='1.0'?><Notice><Publication>775259-2026</Publication></Notice>"
        with patch("src.ted_official_notice_probe.parse_ted_xml",return_value=("x"*200,[])),patch(
                "src.ted_official_notice_probe.extract_ted_lots",return_value=[]):
            report=inspect_notice("775258-2026",
                fetcher=lambda url:(xml,"application/xml",url))
        self.assertFalse(report["notice_identity_found"])
        self.assertFalse(report["official_notice_gate_ready"])

    def test_off_site_and_cross_notice_redirects_rejected(self):
        for final in ["https://attacker.example/en/notice/775258-2026/xml",
                      "https://ted.europa.eu/en/notice/775259-2026/xml",
                      "https://ted.europa.eu/en/"]:
            with self.subTest(url=final):
                with self.assertRaises(ValueError):
                    inspect_notice("775258-2026",
                        fetcher=lambda url:(b"<?xml version='1.0'?><Notice/>",
                                          "application/xml",final))
    def test_safe_classification_never_logs_external_urls(self):
        from urllib.error import HTTPError, URLError
        self.assertEqual(safe_error_code(ValueError("ted_source_not_xml")), "ted_source_not_xml")
        self.assertEqual(safe_error_code(HTTPError("https://private.example", 403, "Forbidden", {}, None)), "ted_http_403")
        self.assertEqual(safe_error_code(URLError("secret.example?token=private")), "ted_network_unreachable")
        self.assertEqual(safe_error_code(ValueError("private_token=secret")), "ValueError")

    def test_invalid_number_rejected_before_network(self):
        with self.assertRaises(ValueError):
            inspect_notice("../invalid",fetcher=lambda _:self.fail("network called"))


if __name__ == "__main__":
    unittest.main()
