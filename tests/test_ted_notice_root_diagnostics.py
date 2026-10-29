"""Aggregate TED diagnostics classify rejected XML error envelopes safely."""
import unittest
from unittest.mock import patch
from src import ted_xml_enricher as ted


class TEDNoticeRootDiagnosticsTests(unittest.TestCase):
    def test_error_envelope_is_classified_without_raw_error_text(self):
        def fail(item):
            item["document_extraction"] = {"attempts": [
                {"source": "ted_xml", "status": "failed",
                 "error": "ValueError:ted_xml_notice_root_missing private-token-123"}
            ]}
            return False

        payload = {"opportunities": [
            {"source": "TED", "publication-number": "681487-2026"}
        ]}
        with patch.object(ted, "enrich_opportunity", side_effect=fail):
            result = ted.enrich_payload(payload)
        report = result["document_extraction"]
        self.assertEqual(
            report["ted_document_failure_stages"]["ted_xml"],
            {"ted_xml_notice_root_missing": 1},
        )
        self.assertNotIn("private-token-123", str(report))


if __name__ == "__main__":
    unittest.main()
