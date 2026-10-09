import unittest
from src.sales_pack import DealBrief, prepare_sales_pack

class SalesPackTests(unittest.TestCase):
    def base(self, **kw):
        data = dict(opportunity_id="RFQ-1", product="steel pipe", buyer_company="Buyer Co",
                    supplier_company="Supplier Co", source_url="https://example.org/rfq")
        data.update(kw)
        return DealBrief(**data)

    def test_no_send_and_no_binding_offer(self):
        x = prepare_sales_pack(self.base())
        self.assertEqual(x["mode"], "shadow")
        self.assertFalse(x["external_actions_allowed"])
        self.assertFalse(x["binding_offer"])
        self.assertFalse(x["ready_for_external_contact"])

    def test_unknown_price_not_fabricated(self):
        x = prepare_sales_pack(self.base())
        self.assertIn("DOĞRULANMIŞ FİYAT", x["offer_text_tr"])
        self.assertIn("verified_price_quote", x["missing_evidence"])

    def test_unverified_quote_is_not_shown(self):
        x = prepare_sales_pack(self.base(unit_price="500", currency="USD", price_quote_verified=False))
        self.assertNotIn("500 USD", x["offer_text_tr"])

    def test_verified_quote_may_be_shown_in_internal_draft(self):
        x = prepare_sales_pack(self.base(unit_price="500", currency="USD", price_quote_verified=True))
        self.assertIn("500 USD", x["offer_text_tr"])

    def test_missing_verification_remains_flagged(self):
        x = prepare_sales_pack(self.base())
        self.assertIn("buyer_verification", x["missing_evidence"])
        self.assertIn("supplier_verification", x["missing_evidence"])

    def test_even_verified_and_consented_remains_shadow(self):
        x = prepare_sales_pack(self.base(buyer_verified=True, supplier_verified=True,
                counterparty_contact_consent=True, unit_price="500", currency="USD",
                price_quote_verified=True, quantity="10", unit="MT",
                grade_specification="ASTM", incoterm="FOB", named_port_or_place="Izmir",
                payment_terms="LC", delivery_terms="30 days"))
        self.assertEqual(x["missing_evidence"], [])
        self.assertFalse(x["ready_for_external_contact"])

    def test_protection_options(self):
        for n in (12, 24, 36):
            self.assertEqual(prepare_sales_pack(self.base(), protection_months=n)
                             ["contract_intake_fields"]["protection_months_proposed"], n)

    def test_reject_unsupported_protection(self):
        with self.assertRaises(ValueError):
            prepare_sales_pack(self.base(), protection_months=60)

    def test_commission_proposal_not_market_claim(self):
        x = prepare_sales_pack(self.base(), proposed_commission_rate="2.5")
        self.assertEqual(x["commission_rate_basis"], "negotiable_proposal_not_market_fact")

    def test_reject_invalid_commission_rate(self):
        for value in ("NaN", "-1", "101"):
            with self.assertRaises(ValueError):
                prepare_sales_pack(self.base(), proposed_commission_rate=value)

    def test_contract_requires_legal_review(self):
        x = prepare_sales_pack(self.base())
        self.assertTrue(x["legal_review_required"])
        self.assertEqual(x["contract_intake_fields"]["governing_law"], "[HUKUKÇU ONAYI]")

if __name__ == "__main__":
    unittest.main()
