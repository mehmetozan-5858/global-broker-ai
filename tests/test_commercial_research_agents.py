import unittest

from src.commercial_research_agents import build


class CommercialResearchAgentsTests(unittest.TestCase):
    def test_verified_supplier_price_blocker_gets_top_priority_price_agent(self):
        payload = {"opportunities": [{
            "id": "OP-1",
            "field_evidence": {"product": {"value": "CNC milling machine"}, "country": {"value": "Saudi Arabia"}},
            "supplier_research": {
                "verified_supplier_count": 1,
                "candidate_suppliers": [{"name": "Example Machines Ltd", "verified": True}],
            },
            "commercial_feasibility": {
                "calculation_ready": False,
                "blockers": ["unit_price", "freight"],
                "missing_inputs": ["unit_price", "freight"],
            },
        }]}
        result = build(payload)
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["tasks"][0]["assigned_agent"], "Price Agent")
        self.assertEqual(result["tasks"][0]["priority"], 100)
        self.assertIn("Example Machines Ltd", result["tasks"][0]["research_query"])
        self.assertFalse(result["external_outreach_enabled"])

    def test_source_terms_agent_handles_quantity_currency_incoterm(self):
        payload = {"opportunities": [{
            "id": "OP-2",
            "title_original": "Industrial pump",
            "commercial_feasibility": {
                "calculation_ready": False,
                "blockers": ["quantity", "currency"],
                "missing_inputs": ["quantity", "currency", "incoterm"],
            },
        }]}
        result = build(payload)
        task = next(t for t in result["tasks"] if t["assigned_agent"] == "Source Terms Agent")
        self.assertIn("quantity", task["reason"])
        self.assertIn("currency", task["reason"])
        self.assertIn("incoterm", task["reason"])
        self.assertTrue(task["source_backed_only"])
        self.assertTrue(task["human_approval_required"])

    def test_calculation_ready_rows_create_no_research_task(self):
        result = build({"opportunities": [{
            "id": "OP-3",
            "commercial_feasibility": {"calculation_ready": True, "blockers": [], "missing_inputs": []},
        }]})
        self.assertEqual(result["task_count"], 0)

    def test_unknown_values_are_never_fabricated(self):
        result = build({"opportunities": [{
            "id": "OP-4",
            "commercial_feasibility": {
                "calculation_ready": False,
                "blockers": ["freight"],
                "missing_inputs": ["freight"],
            },
        }]})
        task = result["tasks"][0]
        self.assertIsNone(task["research_query"])
        self.assertEqual(task["status"], "research_required")


if __name__ == "__main__":
    unittest.main()
