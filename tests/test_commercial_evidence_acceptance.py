import unittest

from src.commercial_evidence_acceptance import process_payload
from src.commercial_feasibility import assess


class CommercialEvidenceAcceptanceTests(unittest.TestCase):
    def base_item(self):
        return {
            "quantity": "100",
            "currency": "USD",
            "delivery_location": "Riyadh",
            "supplier_research": {
                "verified_supplier_count": 1,
                "candidate_suppliers": [{"name": "Example Machines Ltd", "verified": True}],
            },
        }

    def test_verified_supplier_price_and_freight_promote_to_calculation_ready(self):
        item = self.base_item()
        item["commercial_evidence_submissions"] = [
            {
                "kind": "unit_price",
                "value": "12.50",
                "currency": "USD",
                "supplier_name": "Example Machines Ltd",
                "source_url": "https://example.com/quote/123",
            },
            {
                "kind": "freight",
                "value": "500",
                "currency": "USD",
                "origin": "Istanbul",
                "destination": "Riyadh",
                "transport_mode": "road",
                "source_url": "https://forwarder.example/quote/456",
            },
        ]
        payload = {"opportunities": [item]}
        process_payload(payload)
        self.assertEqual(payload["commercial_evidence_acceptance_summary"]["accepted"], 2)
        result = assess(item)
        self.assertTrue(result["calculation_ready"])
        self.assertEqual(item["verified_unit_price"], "12.50")
        self.assertEqual(item["verified_freight"], "500")

    def test_unverified_supplier_price_is_rejected(self):
        item = self.base_item()
        item["commercial_evidence_submissions"] = [{
            "kind": "unit_price",
            "value": "9.90",
            "currency": "USD",
            "supplier_name": "Unknown Supplier",
            "source_url": "https://unknown.example/quote",
        }]
        payload = {"opportunities": [item]}
        process_payload(payload)
        self.assertEqual(payload["commercial_evidence_acceptance_summary"]["accepted"], 0)
        self.assertEqual(payload["commercial_evidence_acceptance_summary"]["rejected"], 1)
        self.assertNotIn("verified_unit_price", item)

    def test_http_evidence_is_rejected(self):
        item = self.base_item()
        item["commercial_evidence_submissions"] = [{
            "kind": "freight",
            "value": "700",
            "currency": "USD",
            "origin": "Istanbul",
            "destination": "Riyadh",
            "source_url": "http://forwarder.example/quote",
        }]
        payload = {"opportunities": [item]}
        process_payload(payload)
        self.assertEqual(payload["commercial_evidence_acceptance_summary"]["rejection_reasons"]["https_source_required"], 1)
        self.assertNotIn("verified_freight", item)

    def test_source_terms_require_official_source_type(self):
        item = self.base_item()
        item.pop("quantity")
        item["commercial_evidence_submissions"] = [
            {
                "kind": "quantity",
                "value": "250 units",
                "source_type": "blog",
                "source_url": "https://example.com/blog",
            },
            {
                "kind": "incoterm",
                "value": "CIF",
                "source_type": "tender_document",
                "source_url": "https://buyer.example/tender.pdf",
            },
        ]
        payload = {"opportunities": [item]}
        process_payload(payload)
        self.assertNotIn("quantity", item)
        self.assertEqual(item["incoterm"], "CIF")
        self.assertEqual(payload["commercial_evidence_acceptance_summary"]["accepted"], 1)
        self.assertEqual(payload["commercial_evidence_acceptance_summary"]["rejected"], 1)

    def test_existing_values_are_not_overwritten(self):
        item = self.base_item()
        item["verified_unit_price"] = "11.00"
        item["commercial_evidence_submissions"] = [{
            "kind": "unit_price",
            "value": "12.50",
            "currency": "USD",
            "supplier_name": "Example Machines Ltd",
            "source_url": "https://example.com/quote/123",
        }]
        process_payload({"opportunities": [item]})
        self.assertEqual(item["verified_unit_price"], "11.00")


if __name__ == "__main__":
    unittest.main()
