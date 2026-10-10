import unittest

from src.supplier_research import prepare, process_payload


class A6SupplierVerificationTests(unittest.TestCase):
    def base_item(self):
        return {
            "title_original": "Industrial measuring equipment",
            "field_evidence": {
                "product": {"value": "Industrial measuring equipment"},
                "country": {"value": "Saudi Arabia"},
            },
            "specification_analysis": {"supplier_sourcing_ready": True},
        }

    def test_supplier_is_verified_only_with_complete_source_evidence(self):
        item = self.base_item()
        item["supplier_candidates"] = [{
            "name": "Example Instruments Ltd",
            "source_url": "https://example.com/products/industrial-measuring-equipment",
            "product_match_evidence": "Manufacturer of industrial measuring equipment and calibration devices",
            "identity_verification_evidence": "Official company website identifies Example Instruments Ltd as manufacturer",
        }]
        result = prepare(item)
        self.assertEqual(result["verified_supplier_count"], 1)
        self.assertEqual(result["status"], "verified_supplier_available")

    def test_missing_identity_evidence_stays_pending(self):
        item = self.base_item()
        item["supplier_candidates"] = [{
            "name": "Example Instruments Ltd",
            "source_url": "https://example.com/products/industrial-measuring-equipment",
            "product_match_evidence": "Industrial measuring equipment",
        }]
        result = prepare(item)
        self.assertEqual(result["verified_supplier_count"], 0)
        self.assertIn("identity_verification_evidence", result["candidate_suppliers"][0]["missing_evidence"])

    def test_non_https_source_is_not_verified(self):
        item = self.base_item()
        item["supplier_candidates"] = [{
            "name": "Example Instruments Ltd",
            "source_url": "http://example.com/product",
            "product_match_evidence": "Industrial measuring equipment",
            "identity_verification_evidence": "Company identity confirmed on source",
        }]
        result = prepare(item)
        self.assertEqual(result["verified_supplier_count"], 0)
        self.assertIn("https_source_url", result["candidate_suppliers"][0]["missing_evidence"])

    def test_unrelated_product_evidence_does_not_verify(self):
        item = self.base_item()
        item["supplier_candidates"] = [{
            "name": "Example Textiles Ltd",
            "source_url": "https://example.com",
            "product_match_evidence": "Manufacturer of cotton shirts",
            "identity_verification_evidence": "Company identity confirmed",
        }]
        result = prepare(item)
        self.assertEqual(result["verified_supplier_count"], 0)

    def test_summary_counts_only_verified_candidates(self):
        item = self.base_item()
        item["supplier_candidates"] = [{
            "name": "Example Instruments Ltd",
            "source_url": "https://example.com",
            "product_match_evidence": "Industrial measuring equipment",
            "identity_verification_evidence": "Official company identity",
        }]
        payload = process_payload({"opportunities": [item]})
        summary = payload["supplier_research_summary"]
        self.assertEqual(summary["verified_suppliers"], 1)
        self.assertEqual(summary["opportunities_with_verified_supplier"], 1)
        self.assertEqual(summary["mode"], "source_verified_candidates")


if __name__ == "__main__":
    unittest.main()
