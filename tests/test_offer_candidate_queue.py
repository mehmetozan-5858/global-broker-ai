import unittest

from src.offer_candidate_queue import build


class OfferCandidateQueueTests(unittest.TestCase):
    def test_only_draft_ready_cases_enter_queue(self):
        payload = {"opportunities": [
            {"id": "READY", "offer_risk_gate": {"draft_offer_ready": True, "risk_flags": []}},
            {"id": "BLOCKED", "offer_risk_gate": {"draft_offer_ready": False, "risk_flags": []}},
        ]}
        result = build(payload)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["queue"][0]["opportunity_id"], "READY")
        self.assertFalse(result["external_action_authorized"])

    def test_risk_case_is_lower_priority_and_human_only(self):
        payload = {"opportunities": [
            {"id": "CLEAN", "offer_risk_gate": {"draft_offer_ready": True, "risk_flags": []}},
            {"id": "RISK", "offer_risk_gate": {"draft_offer_ready": True, "risk_flags": ["single_verified_supplier"]}},
        ]}
        result = build(payload)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["queue"][0]["opportunity_id"], "CLEAN")
        self.assertEqual(result["risk_review_required"], 1)
        self.assertTrue(result["queue"][1]["human_final_approval_required"])
        self.assertIn("submit_bid", result["queue"][1]["forbidden_actions"])


if __name__ == "__main__":
    unittest.main()
