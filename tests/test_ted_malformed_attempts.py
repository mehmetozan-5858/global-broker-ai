"""Malformed TED extraction metadata cannot crash source ingestion or fabricate successes."""
import unittest
from unittest.mock import patch

from src import ted_xml_enricher as ted


class TEDMalformedAttemptsTests(unittest.TestCase):
    def test_invalid_attempt_metadata_is_replaced_by_actual_failure(self):
        for value in ("fake parsed", {"status": "parsed"}, 17, True, [None, "parsed"]):
            with self.subTest(value=value):
                item = {"source": "TED", "publication-number": "681487-2026",
                        "document_extraction": {"attempts": value}}
                with patch.object(ted.document_parser, "_download", side_effect=ValueError("unavailable")):
                    success = ted.enrich_opportunity(item)
                self.assertFalse(success)
                attempts = item["document_extraction"]["attempts"]
                self.assertTrue(attempts)
                self.assertTrue(all(isinstance(a, dict) for a in attempts))
                self.assertFalse(any(a.get("status") == "parsed" for a in attempts))

    def test_aggregate_ignores_malformed_attempts_on_failed_item(self):
        item = {"source": "TED", "publication-number": "681487-2026"}
        def fail(row):
            row["document_extraction"] = {"attempts": "ted_xml:parsed"}
            return False
        with patch.object(ted, "enrich_opportunity", side_effect=fail):
            result = ted.enrich_payload({"opportunities": [item]})
        self.assertEqual(result["document_extraction"]["ted_xml_attempted"], 1)
        self.assertEqual(result["document_extraction"]["ted_xml_parsed"], 0)
        self.assertEqual(result["document_extraction"]["ted_document_failures"], {"unknown": 1})


if __name__ == "__main__":
    unittest.main()
