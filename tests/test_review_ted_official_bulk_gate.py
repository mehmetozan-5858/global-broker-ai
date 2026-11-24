"""Offline negative regression tests for official TED bulk evidence gate."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts" / "review_ted_official_bulk_gate.py"
spec = importlib.util.spec_from_file_location("review_ted_official_bulk_gate", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def valid():
    return {"source_channel": "official_daily_xml_package",
            "package_sha256": "a" * 64,
            "publication_number": "718662-2026",
            "xml_parsed": True, "notice_identity_verified": True,
            "source_completeness_verified": True}


class TedOfficialBulkGateTests(unittest.TestCase):
    def test_202_html_challenge_not_document(self):
        self.assertEqual(mod.classify_response({
            "http_status": 202, "body_kind": "html",
            "challenge_indicator": True, "accepted_as_notice": False
        }), "pending_or_challenged_not_document")

    def test_200_html_not_official_document(self):
        self.assertEqual(mod.classify_response({
            "http_status": 200, "body_kind": "html",
            "accepted_as_notice": True
        }), "not_official_document")

    def test_verified_bulk_manifest_is_not_annex_or_commercial_approval(self):
        result = mod.verify_bulk_manifest(valid(), "718662-2026")
        self.assertTrue(result["bulk_evidence_verified"])
        self.assertFalse(result["annexes_complete"])
        self.assertFalse(result["commercial_approval"])

    def test_unverified_bulk_evidence_rejected(self):
        for key, value in (
            ("source_channel", "unofficial"),
            ("package_sha256", "bad"),
            ("publication_number", "718664-2026"),
            ("xml_parsed", False),
            ("notice_identity_verified", False),
            ("source_completeness_verified", False),
        ):
            with self.subTest(key=key):
                item = valid()
                item[key] = value
                with self.assertRaises(ValueError):
                    mod.verify_bulk_manifest(item, "718662-2026")


if __name__ == "__main__":
    unittest.main()
