import unittest

from src.offer_risk_gate import evaluate, process_payload


class OfferRiskGateA8Tests(unittest.TestCase):
    def ready_item(self):
        return {
            "export_goods_review": {"status": "goods_candidate"},
            "buyer_verification": {"verified": True},
            "specification_analysis": {"supplier_sourcing_ready": True},
            "supplier_research": {"verified_supplier_count": 2},
            "commercial_feasibility": {
                "calculation_ready": True,
                "landed_cost_ready": True,
                "facts": {"destination": {"value": "Doha"}},
            },
            "commercial_terms": {"missing": [], "terms": {}},
        }

    def test_complete_case_is_internal_draft_only(self):
        result = evaluate(self.ready_item())
        self.assertTrue(result["draft_offer_ready"])
        self.assertFalse(result["external_action_authorized"])
        self.assertTrue(result["human_approval_required"])
        self.assertIn("send_email", result["forbidden_actions"])
        self.assertIn("sign_contract", result["forbidden_actions"])

    def test_missing_verified_supplier_blocks_draft(self):
        item = self.ready_item()
        item["supplier_research"]["verified_supplier_count"] = 0
        result = evaluate(item)
        self.assertFalse(result["draft_offer_ready"])
        self.assertIn("verified_supplier", result["blockers"])
        self.assertEqual(result["allowed_actions"], ["internal_review"])

    def test_single_supplier_and_incomplete_landed_cost_raise_risk(self):
        item = self.ready_item()
        item["supplier_research"]["verified_supplier_count"] = 1
        item["commercial_feasibility"]["landed_cost_ready"] = False
        item["commercial_terms"]["missing"] = ["payment", "bond"]
        result = evaluate(item)
        self.assertTrue(result["draft_offer_ready"])
        self.assertTrue(result["risk_review_required"])
        self.assertIn("single_verified_supplier", result["risk_flags"])
        self.assertIn("landed_cost_incomplete", result["risk_flags"])
        self.assertIn("missing_payment_term", result["risk_flags"])
        self.assertIn("missing_bond_term", result["risk_flags"])

    def test_missing_delivery_evidence_blocks_draft(self):
        item = self.ready_item()
        item["commercial_feasibility"]["facts"]["destination"]["value"] = None
        result = evaluate(item)
        self.assertFalse(result["draft_offer_ready"])
        self.assertIn("delivery_evidence", result["blockers"])

    def test_summary_never_authorizes_external_action(self):
        payload = {"opportunities": [self.ready_item()]}
        process_payload(payload)
        summary = payload["offer_risk_summary"]
        self.assertEqual(summary["internal_draft_ready"], 1)
        self.assertEqual(summary["external_action_authorized"], 0)
        self.assertTrue(summary["human_approval_required"])
        self.assertEqual(summary["mode"], "shadow")


if __name__ == "__main__":
    unittest.main()
