"""Reject malformed entries before any live opportunity feed is published."""

import unittest

from src.validate_live_output import validate


class ShadowScanInputIntegrityTests(unittest.TestCase):
    def test_non_object_opportunity_fails_closed(self):
        for invalid in (None, "not-an-opportunity", 42, [], True):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(AssertionError, "malformed opportunity at index 0"):
                    validate({
                        "opportunities": [invalid],
                        "enrichment": {"mode": "source_only_no_hallucination"},
                        "specification_analysis": {"mode": "source_evidence_only"},
                    })

    def test_source_links_count_only_valid_http_candidates(self):
        base = {
            "enrichment": {"mode": "source_only_no_hallucination"},
            "specification_analysis": {"mode": "source_evidence_only"},
        }
        for links, expected in (
            ([""], 0),
            (["javascript:alert(1)"], 0),
            ([None, "not-a-url"], 0),
            ([" https://example.org/tender/123 "], 1),
            (["http://example.org/tender/123"], 1),
        ):
            with self.subTest(links=links):
                payload = {
                    **base,
                    "opportunities": [{
                        "dossier": {"product_name": "Medical supplies", "official_links": links},
                        "specification_analysis": {"status": "document_analysis_pending"},
                    }],
                }
                self.assertEqual(validate(payload)["with_official_links"], expected)

    def test_empty_scan_remains_valid_for_existing_downstream_checks(self):
        result = validate({
            "opportunities": [],
            "enrichment": {"mode": "source_only_no_hallucination"},
        })
        self.assertEqual(result["opportunities"], 0)
        self.assertEqual(result["dossiers"], 0)


if __name__ == "__main__":
    unittest.main()
