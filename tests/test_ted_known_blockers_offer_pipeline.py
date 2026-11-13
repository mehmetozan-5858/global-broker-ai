"""The unresolved specific TED case cannot enter internal offer drafting.

These regressions must not quarantine unrelated tenders or force a global
deployment decision; this is an exact-identifier, review-only risk quarantine.
"""
import unittest

from src.ted_known_blockers import is_quarantined_ted, tender_specific_blockers
from src.offer_risk_gate import evaluate, process_payload
from src.offer_candidate_queue import build


def otherwise_ready():
    return {
        "source": "TED",
        "form-type": "competition",
        "export_goods_review": {"status": "goods_candidate"},
        "buyer_verification": {"verified": True},
        "specification_analysis": {"supplier_sourcing_ready": True},
        "supplier_research": {"verified_supplier_count": 2},
        "commercial_feasibility": {
            "calculation_ready": True,
            "landed_cost_ready": True,
            "facts": {"destination": {"value": "Brno"}},
        },
        "commercial_terms": {"missing": [], "terms": {}},
    }


class TedQuarantineOfferTests(unittest.TestCase):
    def test_unresolved_original_notice_blocks_draft_even_with_other_gates_green(self):
        row = otherwise_ready()
        row["publication-number"] = "702997-2026"
        gate = evaluate(row)
        self.assertFalse(gate["draft_offer_ready"])
        self.assertFalse(gate["external_action_authorized"])
        self.assertEqual(gate["allowed_actions"], ["internal_review"])
        self.assertIn("ted_702997_unresolved_specification_geometry", gate["blockers"])
        self.assertIn("ted_702997_unresolved_drawing_capacity", gate["blockers"])

    def test_amendment_identifier_is_also_blocked(self):
        row = otherwise_ready()
        row["publication-number"] = ["746528-2026"]
        self.assertFalse(evaluate(row)["draft_offer_ready"])

    def test_summary_and_candidate_queue_fail_closed(self):
        row = otherwise_ready()
        row["publication-number"] = "702997-2026"
        payload = process_payload({"opportunities": [row]})
        self.assertEqual(payload["offer_risk_summary"]["internal_draft_ready"], 0)
        self.assertEqual(build(payload)["candidate_count"], 0)

    def test_stale_forged_draft_ready_cannot_enter_queue(self):
        row = {"id": "702997-2026", "offer_risk_gate": {"draft_offer_ready": True, "risk_flags": []}}
        self.assertEqual(build({"opportunities": [row]})["candidate_count"], 0)

    def test_other_cases_are_not_quarantined(self):
        for publication in ("702998-2026", "1702997-2026", "702997-2025"):
            row = otherwise_ready()
            row["publication-number"] = publication
            self.assertFalse(is_quarantined_ted(row))
            self.assertEqual(tender_specific_blockers(row), [])
            self.assertTrue(evaluate(row)["draft_offer_ready"])
            self.assertEqual(build({"opportunities": [row]})["candidate_count"], 1)

    def test_unknown_source_and_absent_notice_do_not_inherit_named_case(self):
        row = otherwise_ready()
        row["title"] = "Discussion of 702997-2026 in prose"
        self.assertFalse(is_quarantined_ted(row))
        self.assertTrue(evaluate(row)["draft_offer_ready"])

    def test_exact_notice_in_identifier_list_is_quarantined(self):
        self.assertTrue(is_quarantined_ted({"publication-number": ["702997-2026", "746528-2026"]}))


if __name__ == "__main__":
    unittest.main()
