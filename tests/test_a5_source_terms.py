import unittest

from src.a5_source_terms import extract, process_payload
from src.commercial_terms import analyze as analyze_commercial_terms


class A5SourceTermsTests(unittest.TestCase):
    def test_conflicting_values_in_one_document_remain_unknown(self):
        item = {"document_extracted_text": "Quantity: 25 pcs\nQuantity: 50 pcs"}
        result = extract(item)
        self.assertNotIn("quantity", item)
        self.assertEqual(result["review_required"]["quantity"], "conflicting_labeled_values")

    def test_conflict_across_source_blocks_is_not_first_match_wins(self):
        item = {"document_extracted_text": "Payment terms: 30 days", "notice_text": "Payment terms: 60 days"}
        result = extract(item)
        self.assertNotIn("payment_terms", item)
        self.assertIn("payment_terms", result["review_required"])

    def test_repeated_equal_values_are_not_a_conflict(self):
        item = {"document_extracted_text": "Quantity: 25 pcs\nQuantity: 25 pcs"}
        self.assertEqual(extract(item)["extracted"], 1)
        self.assertEqual(item["quantity"], "25 pcs")

    def test_unselected_lots_do_not_promote_flat_terms(self):
        item = {"ted_lot_selection_required": True, "document_extracted_text": "Quantity: 25 pcs\nDelivery location: Ankara"}
        result = extract(item)
        self.assertNotIn("quantity", item)
        self.assertNotIn("delivery_location", item)
        self.assertEqual(set(result["review_required"].values()), {"lot_selection_required"})

    def test_structured_aliases_prevent_competing_text_fields(self):
        item = {"quantity-lot": "100 pcs", "deadline-receipt-tender-date-lot": "2026-12-01", "selection-criteria": "ISO 9001", "document_extracted_text": "Quantity: 999 pcs\nSubmission deadline: 2026-12-31\nEligibility: Any bidder"}
        self.assertEqual(extract(item)["extracted"], 0)
        self.assertNotIn("quantity", item)
        self.assertNotIn("deadline", item)
        self.assertNotIn("eligibility", item)

    def test_repeat_preserves_provenance_without_counting_a_new_fact(self):
        item = {"document_extracted_text": "Quantity: 25 pcs"}
        extract(item)
        before = dict(item["a5_source_term_evidence"])
        self.assertEqual(extract(item)["extracted"], 0)
        self.assertEqual(item["a5_source_term_evidence"], before)
        self.assertTrue(analyze_commercial_terms(item)["terms"]["quantity"]["extracted_from_labeled_source_text"])

    def test_changed_fact_does_not_keep_an_old_citation(self):
        item = {"document_extracted_text": "Quantity: 25 pcs"}
        extract(item)
        item["quantity"] = "100 pcs"
        extract(item)
        self.assertNotIn("quantity", item["a5_source_term_evidence"])

    def test_explicit_english_labels_are_promoted(self):
        item = {
            "document_extracted_text": """
            Quantity: 250 units
            Submission deadline: 31 October 2026 14:00
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
        self.assertEqual(result["extracted"], 9)
        self.assertEqual(item["quantity"], "250 units")
        self.assertEqual(item["deadline"], "31 October 2026 14:00")
        self.assertEqual(item["payment_terms"], "30 days after acceptance")
        self.assertEqual(item["bid_bond"], "QAR 50,000")
        self.assertEqual(item["performance_security"], "10% of contract value")
        self.assertEqual(item["delivery_terms"], "CIF Doha")
        self.assertEqual(item["delivery_location"], "Doha warehouse")
        self.assertIn("ISO 9001", item["eligibility"])
        self.assertIn("lowest compliant", item["award_criteria"])

    def test_notice_text_and_equals_separator_are_promoted(self):
        item = {
            "notice_text": "Requested Quantity = 120 pcs\nBid deadline = 20 November 2026\nIncoterm = DDP\nDestination = Riyadh Central Warehouse"
        }
        result = extract(item)
        self.assertEqual(result["extracted"], 4)
        self.assertEqual(item["quantity"], "120 pcs")
        self.assertEqual(item["deadline"], "20 November 2026")
        self.assertEqual(item["delivery_terms"], "DDP")
        self.assertEqual(item["delivery_location"], "Riyadh Central Warehouse")
        self.assertEqual(item["a5_source_term_evidence"]["quantity"]["source_field"], "notice_text")
        self.assertEqual(item["a5_source_term_evidence"]["deadline"]["source_field"], "notice_text")

    def test_unlabelled_free_text_is_not_promoted(self):
        item = {"notice_text": "The buyer may need around 250 units and expects delivery quickly."}
        result = extract(item)
        self.assertEqual(result["extracted"], 0)
        self.assertNotIn("quantity", item)
        self.assertNotIn("deadline", item)
        self.assertNotIn("delivery_terms", item)

    def test_existing_structured_field_wins_over_text_candidate(self):
        item = {
            "quantity": "100 pcs",
            "deadline": "2026-12-01",
            "document_extracted_text": "Quantity: 999 pcs\nSubmission deadline: 2026-12-31\nPayment terms: 15 days",
        }
        extract(item)
        self.assertEqual(item["quantity"], "100 pcs")
        self.assertEqual(item["deadline"], "2026-12-01")
        self.assertEqual(item["payment_terms"], "15 days")
        self.assertNotIn("quantity", item["a5_source_term_evidence"])
        self.assertNotIn("deadline", item["a5_source_term_evidence"])

    def test_arabic_labels_are_source_backed(self):
        item = {"detail_original": "الكمية المطلوبة: 500 جهاز\nآخر موعد للتقديم: 30 نوفمبر 2026\nشروط الدفع: خلال 45 يوم\nشروط التسليم: DDP الرياض"}
        extract(item)
        self.assertEqual(item["quantity"], "500 جهاز")
        self.assertEqual(item["deadline"], "30 نوفمبر 2026")
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
                {"document_extracted_text": "Quantity: 50 pcs\nSubmission deadline: 15 December 2026\nPayment terms: 30 days"},
                {"description-lot": "No labelled commercial facts here"},
            ]
        }
        process_payload(payload)
        summary = payload["a5_source_terms_summary"]
        self.assertEqual(summary["opportunities_with_new_terms"], 1)
        self.assertEqual(summary["new_source_backed_counts"]["quantity"], 1)
        self.assertEqual(summary["new_source_backed_counts"]["deadline"], 1)
        self.assertEqual(summary["new_source_backed_counts"]["payment_terms"], 1)


if __name__ == "__main__":
    unittest.main()
