import unittest

from src.agent_center import build


class AgentCenterA9Tests(unittest.TestCase):
    def test_blocked_opportunity_exposes_next_agent_without_external_action(self):
        payload = {"opportunities": [{
            "id": "opp-1",
            "title_original": "Industrial pump",
            "source_url": "https://example.com/tender",
            "export_goods_review": {"status": "goods_candidate"},
            "core_field_coverage": {"complete": False},
            "specification_analysis": {"supplier_sourcing_ready": False},
            "supplier_research": {"verified_supplier_count": 0},
            "commercial_feasibility": {"calculation_ready": False},
            "offer_risk_gate": {"draft_offer_ready": False},
        }]}
        center = build(payload)
        row = center["work_queue"][0]
        self.assertEqual(row["opportunity_id"], "opp-1")
        self.assertEqual(row["next_agent"], "field_evidence")
        self.assertFalse(row["external_action_authorized"])
        self.assertIn("verified_supplier", row["blockers"])
        self.assertEqual(center["summary"]["blocked"], 1)

    def test_complete_internal_case_routes_to_human_review(self):
        payload = {"opportunities": [{
            "id": "opp-2",
            "source_url": "https://example.com/tender",
            "export_goods_review": {"status": "goods_candidate"},
            "core_field_coverage": {"complete": True},
            "specification_analysis": {"supplier_sourcing_ready": True},
            "supplier_research": {"verified_supplier_count": 2},
            "commercial_feasibility": {"calculation_ready": True},
            "offer_risk_gate": {"draft_offer_ready": True},
        }]}
        center = build(payload)
        row = center["work_queue"][0]
        self.assertEqual(row["blockers"], [])
        self.assertEqual(row["next_agent"], "human_review")
        self.assertEqual(center["summary"]["ready_for_human_review"], 1)
        self.assertFalse(center["external_actions_enabled"])
        self.assertTrue(center["policy"]["human_approval_required"])
        self.assertFalse(center["policy"]["contract_sign"])


if __name__ == "__main__":
    unittest.main()
