"""Aggregate TED failures safely without storing arbitrary exception details."""

import unittest
from unittest.mock import patch
from src import ted_xml_enricher


class TedFailureTelemetryTests(unittest.TestCase):
    def test_failures_are_counted_without_exposing_urls_or_exception_text(self):
        rows = [
            {"source": "TED", "publication-number": "123-2026"},
            {"source": "TED", "publication-number": "124-2026"},
            {"source": "TED", "publication-number": "125-2026"},
        ]
        failures = [
            [{"source": "ted_xml", "status": "failed", "error": "ValueError:ted_source_not_xml"}],
            [{"source": "ted_xml", "status": "failed", "error": "ValueError:unexpected token=secret-123"}],
            [],
        ]
        def fail(row):
            row["document_extraction"] = {"attempts": failures[rows.index(row)]}
            return False
        with patch.object(ted_xml_enricher, "enrich_opportunity", side_effect=fail):
            result = ted_xml_enricher.enrich_payload({"opportunities": rows})
        summary = result["document_extraction"]
        self.assertEqual(summary["ted_xml_attempted"], 3)
        self.assertEqual(summary["ted_document_failed_notices"], 3)
        self.assertEqual(summary["ted_document_failures"], {
            "other": 1, "ted_source_not_xml": 1, "unknown": 1,
        })
        self.assertNotIn("secret-123", str(summary))

    def test_successful_fallback_is_not_counted_as_failed_notice(self):
        row = {"source": "TED", "publication-number": "123-2026"}
        def succeed(item):
            item["document_extraction"] = {
                "ted_xml_parsed": False, "ted_html_parsed": True,
                "parsed_count": 1,
                "attempts": [{"source": "ted_xml", "status": "failed",
                              "error": "ValueError:ted_source_not_xml"}],
            }
            return True
        with patch.object(ted_xml_enricher, "enrich_opportunity", side_effect=succeed):
            result = ted_xml_enricher.enrich_payload({"opportunities": [row]})
        self.assertEqual(result["document_extraction"]["ted_document_failed_notices"], 0)
        self.assertEqual(result["document_extraction"]["ted_html_parsed"], 1)


if __name__ == "__main__":
    unittest.main()
