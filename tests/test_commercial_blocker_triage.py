import unittest

from src.commercial_blocker_triage import build


class CommercialBlockerTriageTests(unittest.TestCase):
    def test_counts_missing_facts_and_keeps_queue_research_only(self):
        payload = {"opportunities": [
            {
                "id": "A1", "source_url": "https://example.org/tender",
                "field_evidence": {"product": {"value": "CNC machine"}},
                "supplier_research": {"verified_supplier_count": 0},
                "commercial_feasibility": {
                    "calculation_ready": False,
                    "blockers": ["quantity", "unit_price", "freight"],
                    "missing_inputs": ["quantity", "unit_price", "freight"],
                },
            },
            {
                "id": "B2",
                "commercial_feasibility": {
                    "calculation_ready": False,
                    "blockers": ["unit_price"],
                    "missing_inputs": ["unit_price"],
                },
            },
        ]}
        result = build(payload)
        self.assertEqual(result["blocker_counts"]["unit_price"], 2)
        self.assertEqual(result["research_queue_count"], 2)
        self.assertEqual(result["research_queue"][0]["opportunity_id"], "A1")
        self.assertTrue(result["research_queue"][0]["human_approval_required"])
        self.assertFalse(result["external_outreach_enabled"])

    def test_calculation_ready_does_not_enter_queue(self):
        result = build({"opportunities": [
            {"commercial_feasibility": {"calculation_ready": True, "blockers": []}}
        ]})
        self.assertEqual(result["calculation_ready"], 1)
        self.assertEqual(result["research_queue_count"], 0)


if __name__ == "__main__":
    unittest.main()
