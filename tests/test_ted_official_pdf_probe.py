import unittest
from src.ted_official_pdf_probe import probe_pdf


class OfficialSignedPdfProbeTests(unittest.TestCase):
    def test_pdf_transport_can_pass_without_any_commercial_or_document_acceptance(self):
        raw=b"%PDF-1.7\n"+b"x"*200
        result=probe_pdf("775258-2026",fetcher=lambda url:(raw,url))
        self.assertTrue(result["signed_pdf_transport"])
        self.assertEqual(len(result["sha256"]),64)
        for key in ["notice_identity_verified","pdf_visual_review_verified",
                    "annexes_verified","revision_verified","commercial_acceptance"]:
            self.assertFalse(result[key])

    def test_empty_or_html_is_rejected(self):
        for data in [b"",b"<html><body>error</body></html>",b"%PDF-1.7"]:
            with self.subTest(length=len(data)),self.assertRaises(ValueError):
                probe_pdf("775258-2026",fetcher=lambda url:(data,url))

    def test_cross_notice_redirect_never_counts(self):
        with self.assertRaisesRegex(ValueError,"ted_document_notice_redirect_mismatch"):
            probe_pdf("775258-2026",fetcher=lambda url:(b"%PDF-1.7\n"+b"x"*200,
                "https://ted.europa.eu/en/notice/775259-2026/pdfs"))


if __name__=="__main__":
    unittest.main()
