"""TED aggregate diagnostics retain the failure of each attempted document format."""
import unittest
from unittest.mock import patch
from src import ted_xml_enricher as ted


class StageDiagnosticsTests(unittest.TestCase):
    def _payload(self):
        return {"opportunities": [{"source": "TED", "publication-number": "681487-2026"}]}

    def test_pdf_fallback_does_not_hide_xml_and_html_errors(self):
        def unsuccessful(item):
            item["document_extraction"] = {"attempts": [
                {"source": "ted_xml", "status": "failed", "error": "ValueError:ted_source_not_xml"},
                {"source": "ted_html_download", "status": "failed", "error": "ValueError:ted_document_notice_identity_or_text_missing"},
                {"source": "ted_pdf_download", "status": "failed", "error": "ValueError:ted_pdf_download_not_pdf"},
            ]}
            return False

        with patch.object(ted, "enrich_opportunity", side_effect=unsuccessful):
            result = ted.enrich_payload(self._payload())
        report = result["document_extraction"]
        self.assertEqual(report["ted_document_failed_notices"], 1)
        self.assertEqual(report["ted_document_failures"], {"ted_pdf_download_not_pdf": 1})
        self.assertEqual(report["ted_document_failure_stages"], {
            "ted_xml": {"ted_source_not_xml": 1},
            "ted_html_download": {"ted_document_notice_identity_or_text_missing": 1},
            "ted_pdf_download": {"ted_pdf_download_not_pdf": 1},
        })

    def test_unknown_exceptions_are_classified_without_raw_message_leakage(self):
        def unsuccessful(item):
            item["document_extraction"] = {"attempts": [
                {"source": "ted_xml", "status": "failed", "error": "private token or sensitive URL"},
            ]}
            return False

        with patch.object(ted, "enrich_opportunity", side_effect=unsuccessful):
            result = ted.enrich_payload(self._payload())
        report = result["document_extraction"]
        self.assertEqual(report["ted_document_failure_stages"]["ted_xml"], {"other": 1})
        self.assertNotIn("private token", str(report))
        self.assertEqual(report["ted_document_failure_stages"]["ted_pdf_download"], {})


if __name__ == "__main__":
    unittest.main()
