import unittest

from src.a5_source_terms import extract, process_payload
from src.commercial_terms import analyze as analyze_commercial_terms


class A5SourceTermsTests(unittest.TestCase):
    def test_explicit_english_labels_are_promoted(self):
        item = {
            "document_extracted_text": """
            Quantity: 250 units
            Payment terms: 30 days after acceptance
            Bid bond: QAR 50,000
            Performance security: 10% of contract value
            Delivery terms: CIF Doha
            Delivery location: Doha warehouse
            Eligibility: ISO 9001 certified manufacturer with 3 years experience
            Award criteria: lowest compliant evaluated price
            """
        }
        result = extract(item)
        self.assertEqual(result["extracted"], 8)
        self.assertEqual(item["quantity"], "250 units")
        self.assertEqual(item["payment_terms"], "30 days after acceptance")
        self.assertEqual(item["bid_bond"], "QAR 50,000")
        self.assertEqual(item["performance_security"], "10% of contract value")
        self.assertEqual(item["delivery_terms"], "CIF Doha")
        self.assertEqual(item["delivery_location"], "Doha warehouse")
        self.assertIn("ISO 9001", item["eligibility"])
        self.assertIn("lowest compliant", item["award_criteria"])

    def test_unlabelled_free_text_is_not_promoted(self):
        item = {"document_extracted_text": "The buyer may need around 250 units and expects delivery quickly."}
        result = extract(item)
        self.assertEqual(result["extracted"], 0)
        self.assertNotIn("quantity", item)
        self.assertNotIn("delivery_terms", item)

    def test_existing_structured_field_wins_over_text_candidate(self):
        item = {
            "quantity": "100 pcs",
            "document_extracted_text": "Quantity: 999 pcs\nPayment terms: 15 days",
        }
        extract(item)
        self.assertEqual(item["quantity"], "100 pcs")
        self.assertEqual(item["payment_terms"], "15 days")
        self.assertNotIn("quantity", item["a5_source_term_evidence"])

    def test_arabic_labels_are_source_backed(self):
        item = {"detail_original": "الكمية: 500 جهاز\nشروط الدفع: خلال 45 يوم\nشروط التسليم: DDP الرياض"}
        extract(item)
        self.assertEqual(item["quantity"], "500 جهاز")
        self.assertEqual(item["payment_terms"], "خلال 45 يوم")
        self.assertEqual(item["delivery_terms"], "DDP الرياض")

    def test_commercial_terms_preserve_provenance(self):
        item = {"document_extracted_text": "Quantity: 25 units\nBid bond: USD 1,000"}
        extract(item)
        terms = analyze_commercial_terms(item)["terms"]
        self.assertTrue(terms["quantity"]["extracted_from_labeled_source_text"])
        self.assertEqual(terms["quantity"]["evidence_source_field"], "document_extracted_text")
        self.assertTrue(terms["bond"]["extracted_from_labeled_source_text"])
        self.assertEqual(terms["payment"]["status"], "missing")

    def test_payload_summary_counts_only_new_explicit_terms(self):
        payload = {
            "opportunities": [
                {"document_extracted_text": "Quantity: 50 pcs\nPayment terms: 30 days"},
                {"description-lot": "No labelled commercial facts here"},
            ]
        }
        process_payload(payload)
        summary = payload["a5_source_terms_summary"]
        self.assertEqual(summary["opportunities_with_new_terms"], 1)
        self.assertEqual(summary["new_source_backed_counts"]["quantity"], 1)
        self.assertEqual(summary["new_source_backed_counts"]["payment_terms"], 1)


if __name__ == "__main__":
    unittest.main()
