"""Scoped review-branch defense against premature TED 702997-2026 price readiness."""
from copy import deepcopy
from datetime import date
import unittest

from src.price_margin_gate import assess

TODAY = date(2026, 11, 14)


def fully_evidenced_fixture():
    # Test fixture only. Fake sources and quotes; no commercial data.
    return {
        "notice_id": "other-notice",
        "quantity": "10",
        "verified_unit_price": "100",
        "verified_unit_price_source": "https://example.invalid/supplier",
        "verified_unit_price_supplier": "Synthetic Supplier",
        "quote_currency": "EUR",
        "supplier_quote_reference": "SYN-001",
        "supplier_quote_date": "2026-11-12",
        "supplier_price_unit": "piece",
        "supplier_quantity_basis": "10",
        "quote_valid_until": "2026-12-01",
        "supplier_research": {"candidate_suppliers": [{
            "name": "Synthetic Supplier",
            "verified": True,
            "financial_evidence_eligible": True,
        }]},
        "verified_selling_unit_price": "120",
        "verified_selling_price_source": "https://example.invalid/buyer",
        "selling_currency": "EUR",
        "selling_quote_buyer": "Synthetic Buyer",
        "buyer_quote_reference": "SYN-002",
        "buyer_quote_date": "2026-11-12",
        "buyer_price_unit": "piece",
        "buyer_quantity_basis": "10",
    }


class TedPriceReadinessHoldTests(unittest.TestCase):
    def test_other_notice_keeps_unrelated_logic(self):
        result = assess(fully_evidenced_fixture(), TODAY)
        self.assertTrue(result["price_ready"])
        self.assertTrue(result["margin_ready"])
        self.assertIn("gross_product_spread", result)

    def test_exact_ted_notice_blocks_price_and_margin_even_if_fully_quoted(self):
        for field in ("notice_id", "ted_notice_id", "source_notice_id"):
            with self.subTest(field=field):
                item = fully_evidenced_fixture()
                item[field] = "702997-2026"
                result = assess(item, TODAY)
                self.assertFalse(result["price_ready"])
                self.assertFalse(result["margin_ready"])
                self.assertEqual(result["status"], "research_required")
                self.assertIn("ted_702997_2026_unresolved_technical_capacity_conflict", result["missing_or_invalid"])
                self.assertNotIn("gross_product_spread", result)
                self.assertFalse(result["external_outreach_enabled"])

    def test_original_amendment_and_official_ted_url_share_hold(self):
        cases = (
            {"publication-number": "702997-2026"},
            {"publication-number": ["746528-2026"]},
            {"publication_number": "746528-2026"},
            {"notice_id": "746528-2026"},
            {"source_url": "https://ted.europa.eu/en/notice/-/detail/746528-2026"},
            {"official_links": ["https://ted.europa.eu/cs/notice/-/detail/702997-2026"]},
        )
        for fields in cases:
            with self.subTest(fields=fields):
                item = fully_evidenced_fixture()
                item.update(fields)
                status = assess(item, TODAY)
                self.assertFalse(status["price_ready"])
                self.assertFalse(status["margin_ready"])
                self.assertNotIn("gross_product_spread", status)
                self.assertIn("ted_702997_2026_unresolved_technical_capacity_conflict",
                              status["missing_or_invalid"])

    def test_lookalike_domain_and_invalid_url_cannot_trigger_ted_quarantine(self):
        urls = (
            "https://ted.europa.eu.attacker.invalid/en/notice/-/detail/702997-2026",
            "https://ted.europa.eu/en/notice/-/detail/702997-2026-extra",
            "https://ted.europa.eu/en/notice/-/detail/702997-2026?other=1",
        )
        for value in urls:
            with self.subTest(value=value):
                item = fully_evidenced_fixture()
                item["source_url"] = value
                self.assertTrue(assess(item, TODAY)["price_ready"])

    def test_preapproved_or_untrusted_evidence_field_cannot_override_hold(self):
        item = fully_evidenced_fixture()
        item.update(notice_id="702997-2026", technical_approval=True, capacity_verified=True)
        result = assess(item, TODAY)
        self.assertFalse(result["price_ready"])
        self.assertNotIn("gross_product_spread", result)

    def test_near_matches_are_not_arbitrarily_blocked(self):
        for value in ("702997-2025", "1702997-2026", "702997-2026-extra"):
            with self.subTest(value=value):
                item = fully_evidenced_fixture()
                item["notice_id"] = value
                self.assertTrue(assess(item, TODAY)["price_ready"])


if __name__ == "__main__":
    unittest.main()
