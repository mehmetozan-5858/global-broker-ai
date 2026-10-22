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

    def test_empty_scan_remains_valid_for_existing_downstream_checks(self):
        result = validate({
            "opportunities": [],
            "enrichment": {"mode": "source_only_no_hallucination"},
        })
        self.assertEqual(result["opportunities"], 0)
        self.assertEqual(result["dossiers"], 0)


if __name__ == "__main__":
    unittest.main()
