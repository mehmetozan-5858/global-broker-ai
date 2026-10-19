import unittest
from datetime import date
from src.price_margin_gate import assess, process_payload


def example():
    return {
        "id": "op-1",
        "quantity": "100",
        "verified_unit_price": "12.50",
        "quote_currency": "USD",
        "verified_unit_price_source": "https://manufacturer.example/quote/123",
        "verified_unit_price_supplier": "Maker Ltd",
        "quote_valid_until": "2026-12-31",
        "supplier_quote_reference": "Q-123",
        "supplier_quote_date": "2026-10-10",
        "supplier_price_unit": "per unit",
        "supplier_quantity_basis": "100",
        "verified_selling_unit_price": "18",
        "selling_currency": "USD",
        "verified_selling_price_source": "https://buyer.example/offer/789",
        "selling_quote_buyer": "Buyer Agency",
        "buyer_quote_reference": "B-789",
        "buyer_quote_date": "2026-10-11",
        "buyer_price_unit": "per unit",
        "buyer_quantity_basis": "100",
        "supplier_research": {"verified_supplier_count": 1, "candidate_suppliers": [
            {"name": "Maker Ltd", "verified": True, "financial_evidence_eligible": True}
        ]},
    }


class PriceMarginGateTests(unittest.TestCase):
    def test_gross_spread_only_with_valid_evidence(self):
        row = example()
        result = assess(row, date(2026, 10, 12))
        self.assertTrue(result["margin_ready"])
        self.assertEqual(result["gross_product_spread"], "550.00")
        self.assertNotIn("net_profit", result)

    def test_unselected_multiple_lots_block_even_valid_quotes(self):
        row=example();row["ted_lot_selection_required"]=True
        result=assess(row,date(2026,10,12))
        self.assertFalse(result["price_ready"])
        self.assertFalse(result["margin_ready"])
        self.assertNotIn("gross_product_spread",result)
        self.assertIn("lot_selection",result["missing_or_invalid"])

    def test_expired_quote_fails_closed(self):
        row = example()
        row["quote_valid_until"] = "2026-01-01"
        result = assess(row, date(2026, 10, 12))
        self.assertFalse(result["price_ready"])
        self.assertIn("quote_expired", result["missing_or_invalid"])

    def test_mismatched_currency_blocks_spread(self):
        row = example()
        row["selling_currency"] = "EUR"
        self.assertFalse(assess(row, date(2026, 10, 12))["margin_ready"])

    def test_no_source_or_financially_ineligible_supplier_blocks(self):
        row = example()
        row["verified_unit_price_source"] = "http://fake.example/quote"
        self.assertFalse(assess(row, date(2026, 10, 12))["price_ready"])
        row = example()
        row["supplier_research"]["candidate_suppliers"][0]["financial_evidence_eligible"] = False
        self.assertFalse(assess(row, date(2026, 10, 12))["price_ready"])
        self.assertIn("financially_eligible_exact_spec_supplier", row["price_margin_gate"]["missing_or_invalid"])

    def test_stage3_verified_flag_alone_is_not_enough_for_money_claim(self):
        row = example()
        row["supplier_research"]["candidate_suppliers"] = [{"name": "Maker Ltd", "verified": True}]
        result = assess(row, date(2026, 10, 12))
        self.assertFalse(result["price_ready"])
        self.assertIn("financially_eligible_exact_spec_supplier", result["missing_or_invalid"])

    def test_missing_quote_metadata_blocks_price_readiness(self):
        for field, blocker in (
            ("supplier_quote_reference", "supplier_quote_reference"),
            ("supplier_quote_date", "supplier_quote_date"),
            ("supplier_price_unit", "supplier_price_unit"),
            ("supplier_quantity_basis", "supplier_quantity_basis"),
        ):
            row = example()
            row.pop(field)
            result = assess(row, date(2026, 10, 12))
            self.assertFalse(result["price_ready"], field)
            self.assertIn(blocker, result["missing_or_invalid"])

    def test_missing_buyer_metadata_blocks_margin_not_supplier_price(self):
        row = example()
        row.pop("buyer_quote_reference")
        result = assess(row, date(2026, 10, 12))
        self.assertTrue(result["price_ready"])
        self.assertFalse(result["margin_ready"])
        self.assertIn("buyer_quote_reference", result["missing_or_invalid"])

    def test_negative_spread_is_not_hidden(self):
        row = example()
        row["verified_selling_unit_price"] = "10"
        result = assess(row, date(2026, 10, 12))
        self.assertTrue(result["negative_spread"])
        self.assertEqual(result["gross_product_spread"], "-250.00")

    def test_invalid_or_missing_quote_not_fabricated(self):
        row = example()
        row["verified_unit_price"] = "unknown"
        row["quote_valid_until"] = None
        result = process_payload({"opportunities": [row]}, date(2026, 10, 12))
        self.assertEqual(result["price_margin_summary"]["gross_spread_ready"], 0)
        self.assertEqual(result["price_margin_summary"]["research_queue_count"], 1)


if __name__ == "__main__":
    unittest.main()
