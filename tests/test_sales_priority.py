import unittest

from src.sales_priority import enrich_payload, sales_priority


class SalesPriorityTests(unittest.TestCase):
    def test_fully_backed_opportunity_is_close_first(self):
        item = {
            "buyer_verification": {"status": "verified", "evidence": ["official_registry"]},
            "supplier_ready": True,
            "supplier_status": "verified",
            "compliance_status": "clear",
            "margin_status": "positive",
            "estimated_value": 250000,
            "deadline": "2026-11-30",
            "source_url": "https://example.org/notice/1",
            "document_extraction": {"status": "parsed", "parsed_count": 1},
        }
        out = sales_priority(item)
        self.assertEqual(out["grade"], "A")
        self.assertEqual(out["queue"], "close_first")
        self.assertTrue(out["source_backed_only"])
        self.assertGreaterEqual(out["score"], 75)

    def test_unknown_data_gets_no_positive_credit(self):
        out = sales_priority({})
        self.assertEqual(out["score"], 0)
        self.assertEqual(out["grade"], "C")
        self.assertEqual(out["queue"], "research_only")
        self.assertIn("buyer_verification", out["blockers"])
        self.assertIn("supplier_verification", out["blockers"])

    def test_unverified_buyer_name_does_not_count(self):
        out = sales_priority({"buyer": "Named Buyer", "source_url": "https://example.org/notice/2"})
        self.assertNotIn("verified_buyer", out["reasons"])
        self.assertIn("buyer_verification", out["blockers"])

    def test_payload_summary_counts_grades(self):
        payload = {
            "opportunities": [
                {
                    "buyer_verification": {"status": "verified", "evidence": ["registry"]},
                    "supplier_ready": True,
                    "supplier_status": "verified",
                    "compliance_status": "clear",
                    "margin_status": "positive",
                    "estimated_value": 1000,
                    "deadline": "2026-12-01",
                    "source_url": "https://example.org/a",
                    "document_extraction": {"status": "parsed", "parsed_count": 1},
                },
                {},
            ]
        }
        enrich_payload(payload)
        summary = payload["sales_priority_summary"]
        self.assertEqual(summary["close_first"], 1)
        self.assertEqual(summary["research_only"], 1)


if __name__ == "__main__":
    unittest.main()
