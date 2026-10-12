import unittest
from datetime import date

from src.stage4_supplier_financial_gate import process_payload as process_supplier_gate
from src.price_margin_gate import process_payload as process_price
from src.commercial_evidence_acceptance import process_payload as process_evidence
from src.stage4_completion import build as build_completion


class Stage4FinancialGateTests(unittest.TestCase):
    def candidate_item(self):
        return {
            "id": "op-4",
            "quantity": "100",
            "supplier_research": {
                "verified_supplier_count": 1,
                "candidate_suppliers": [{
                    "name": "Maker Ltd",
                    "verified": True,
                    "source_url": "https://maker.example",
                    "product_match_evidence": "Exact product family",
                    "identity_verification_evidence": "Registered manufacturer",
                }],
            },
        }

    def test_stage3_verified_alone_is_not_financially_eligible(self):
        item = self.candidate_item()
        process_supplier_gate({"opportunities": [item]})
        self.assertNotIn("financial_evidence_eligible", item["supplier_research"]["candidate_suppliers"][0])

    def test_exact_spec_evidence_promotes_financial_eligibility(self):
        item = self.candidate_item()
        item["supplier_financial_evidence"] = [{
            "supplier_name": "Maker Ltd",
            "exact_spec_match": True,
            "exact_spec_source_url": "https://buyer.example/spec/1",
            "identity_evidence_url": "https://registry.example/maker",
            "product_evidence_url": "https://maker.example/product/1",
            "specification_reference": "SPEC-001",
        }]
        payload = {"opportunities": [item]}
        process_supplier_gate(payload)
        candidate = item["supplier_research"]["candidate_suppliers"][0]
        self.assertTrue(candidate["financial_evidence_eligible"])
        self.assertEqual(payload["stage4_supplier_financial_summary"]["eligible_suppliers"], 1)

    def test_missing_exact_spec_source_fails_closed(self):
        item = self.candidate_item()
        item["supplier_financial_evidence"] = [{
            "supplier_name": "Maker Ltd",
            "exact_spec_match": True,
            "exact_spec_source_url": "http://buyer.example/spec/1",
            "identity_evidence_url": "https://registry.example/maker",
            "product_evidence_url": "https://maker.example/product/1",
            "specification_reference": "SPEC-001",
        }]
        payload = {"opportunities": [item]}
        process_supplier_gate(payload)
        self.assertEqual(payload["stage4_supplier_financial_summary"]["eligible_suppliers"], 0)
        self.assertEqual(payload["stage4_supplier_financial_summary"]["rejected"], 1)

    def test_full_stage4_evidence_can_reach_margin_ready(self):
        item = self.candidate_item()
        item["supplier_financial_evidence"] = [{
            "supplier_name": "Maker Ltd",
            "exact_spec_match": True,
            "exact_spec_source_url": "https://buyer.example/spec/1",
            "identity_evidence_url": "https://registry.example/maker",
            "product_evidence_url": "https://maker.example/product/1",
            "specification_reference": "SPEC-001",
        }]
        item["commercial_evidence_submissions"] = [
            {
                "kind": "unit_price", "value": "12.50", "currency": "USD",
                "supplier_name": "Maker Ltd", "source_url": "https://maker.example/quote/Q1",
                "valid_until": "2026-12-31", "quote_reference": "Q1", "quote_date": "2026-10-10",
                "price_unit": "per unit", "quantity_basis": "100",
            },
            {
                "kind": "selling_unit_price", "value": "18", "currency": "USD",
                "buyer_name": "Buyer Agency", "source_url": "https://buyer.example/price/B1",
                "quote_reference": "B1", "quote_date": "2026-10-11",
                "price_unit": "per unit", "quantity_basis": "100",
            },
        ]
        payload = {"opportunities": [item], "pilot_dossier_summary": {"selected_count": 1}}
        process_supplier_gate(payload)
        process_evidence(payload)
        process_price(payload, date(2026, 10, 12))
        build_completion(payload)
        self.assertTrue(item["price_margin_gate"]["margin_ready"])
        self.assertTrue(payload["stage4_completion"]["engine_complete"])
        self.assertTrue(payload["stage4_completion"]["live_commercial_data_ready"])
        self.assertNotIn("net_profit", item["price_margin_gate"])

    def test_engine_complete_does_not_fake_live_data(self):
        payload = {
            "opportunities": [],
            "stage4_supplier_financial_summary": {"fail_closed": True, "eligible_suppliers": 0},
            "commercial_evidence_acceptance_summary": {"source_backed_only": True, "fail_closed": True},
            "price_margin_summary": {
                "evidence_standard": "v2_exact_spec_complete_quote_metadata",
                "price_ready": 0,
                "gross_spread_ready": 0,
                "net_profit_calculated": False,
                "human_approval_required": True,
            },
            "pilot_dossier_summary": {"selected_count": 0},
        }
        build_completion(payload)
        self.assertTrue(payload["stage4_completion"]["engine_complete"])
        self.assertFalse(payload["stage4_completion"]["live_commercial_data_ready"])
        self.assertEqual(payload["stage4_completion"]["status"], "complete_engine_live_data_pending")


if __name__ == "__main__":
    unittest.main()
