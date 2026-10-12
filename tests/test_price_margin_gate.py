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
        "verified_selling_unit_price": "18",
        "selling_currency": "USD",
        "verified_selling_price_source": "https://buyer.example/offer/789",
        "supplier_research": {"verified_supplier_count": 1, "candidate_suppliers": [
            {"name": "Maker Ltd", "verified": True}
        ]},
    }


class PriceMarginGateTests(unittest.TestCase):
    def test_gross_spread_only_with_valid_evidence(self):
        row = example()
        result = assess(row, date(2026, 10, 12))
        self.assertTrue(result["margin_ready"])
        self.assertEqual(result["gross_product_spread"], "550.00")
        self.assertNotIn("net_profit", result)

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

    def test_no_source_or_unverified_supplier_blocks(self):
        row = example()
        row["verified_unit_price_source"] = "http://fake.example/quote"
        self.assertFalse(assess(row, date(2026, 10, 12))["price_ready"])
        row = example()
        row["supplier_research"]["candidate_suppliers"] = []
        self.assertFalse(assess(row, date(2026, 10, 12))["price_ready"])

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
