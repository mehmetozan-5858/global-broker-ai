import unittest
from datetime import date
from src.pipeline import build_ceo_case, ceo_summary, trade_route
from src.matching import TradeIntent
from src.sales_pack import DealBrief
from src.commission import CommissionTerms

class PipelineTests(unittest.TestCase):
    def opportunity(self, **kw):
        row = {"id":"RFQ-1", "source":"TED", "source_url":"https://ted.europa.eu/example",
               "title_original":"steel pipe", "buyer-name":"Buyer Ltd",
               "buyer-country":"Germany", "deadline-receipt-tender-date-lot":"2026-11-01"}
        row.update(kw)
        return row

    def test_groups(self):
        self.assertEqual(trade_route("Germany","Turkey"), "turkey_export")
        self.assertEqual(trade_route("Turkey","China"), "turkey_import")
        self.assertEqual(trade_route("Brazil","India"), "third_country_brokerage")
        self.assertEqual(trade_route("Turkey","Turkey"), "domestic_turkey_review")
        self.assertEqual(trade_route("Germany",""), "route_pending")

    def test_name_alone_never_verifies(self):
        x = build_ceo_case(self.opportunity(), today=date(2026,10,9))
        self.assertFalse(x["buyer_verified"])
        self.assertIn("buyer_verification", x["blockers"])

    def test_expired_is_archived(self):
        x = build_ceo_case(self.opportunity(**{"deadline-receipt-tender-date-lot":"2026-10-01"}),
                           today=date(2026,10,9))
        self.assertEqual(x["ceo_priority"], "ARCHIVE_EXPIRED")
        self.assertIn("deadline_expired", x["blockers"])

    def test_public_tender_not_private_mandate(self):
        x = build_ceo_case(self.opportunity(), today=date(2026,10,9))
        self.assertIn("public_tender_not_private_buyer_mandate", x["blockers"])

    def test_incompatible_supplier_blocked(self):
        seller = TradeIntent(id="S1", side="SELL", product="wheat", country="Turkey")
        x = build_ceo_case(self.opportunity(), seller=seller, today=date(2026,10,9))
        self.assertIn("supplier_incompatible", x["blockers"])
        self.assertFalse(x["external_actions_allowed"])

    def test_no_contact_authorization_even_with_consent(self):
        seller = TradeIntent(id="S1", side="SELL", product="steel pipe", country="Turkey",
                             company_verified=True, contact_consent=True)
        deal = DealBrief(opportunity_id="RFQ-1", product="steel pipe",
                         buyer_country="Germany", supplier_country="Turkey",
                         buyer_verified=True, supplier_verified=True, counterparty_contact_consent=True)
        x = build_ceo_case(self.opportunity(), seller=seller, deal=deal, today=date(2026,10,9))
        self.assertFalse(x["sales_pack"]["ready_for_external_contact"])
        self.assertFalse(x["contract_signature_allowed"])

    def test_no_commission_fabrication(self):
        x = build_ceo_case(self.opportunity(), commission_terms=CommissionTerms(payer="supplier",currency="USD"),
                           today=date(2026,10,9))
        self.assertIsNone(x["commission"]["commission_amount_estimate"])

    def test_ceo_grouping(self):
        a = build_ceo_case(self.opportunity(), deal=DealBrief(opportunity_id="RFQ-1", product="steel pipe",
                            buyer_country="Germany", supplier_country="Turkey"), today=date(2026,10,9))
        s = ceo_summary([a])
        self.assertEqual(len(s["groups"]["turkey_export"]), 1)
        self.assertEqual(s["new_verified_sales"], 0)
        self.assertIsNone(s["realized_commission"])

if __name__ == "__main__":
    unittest.main()
