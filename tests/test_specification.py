import unittest

from src.specification import analyze_opportunity, analyze_payload


class SpecificationEvidenceTests(unittest.TestCase):
    def test_explicit_source_fields_are_preserved_as_evidence(self):
        item = {
            "technical-specification": "Accuracy 0.1 mg; ISO 9001 certificate required.",
            "quantity-lot": "12",
            "quantity-unit-lot": "pieces",
            "place-of-performance-city-lot": "Bucharest",
            "dossier": {},
            "workflow": {},
        }
        out = analyze_opportunity(item)
        spec = out["specification_analysis"]
        self.assertEqual(spec["status"], "source_fields_analyzed")
        self.assertEqual(spec["quantity_evidence"][0]["field"], "quantity-lot")
        self.assertIn("ISO 9001", spec["standards"])
        self.assertEqual(out["dossier"]["specification_status"], "source_fields_analyzed")

    def test_pdf_is_marked_for_parser_not_claimed_as_read(self):
        item = {
            "official_links": ["https://ted.europa.eu/specification.pdf"],
            "dossier": {},
            "workflow": {},
        }
        out = analyze_opportunity(item)
        spec = out["specification_analysis"]
        self.assertEqual(spec["status"], "document_analysis_pending")
        self.assertTrue(spec["attachment_requires_parsing"])
        self.assertEqual(spec["documents"][0]["kind"], "pdf")
        self.assertFalse(spec["technical_evidence"])

    def test_source_page_without_details_stays_pending(self):
        item = {
            "source_url": "https://ted.europa.eu/en/notice/-/detail/123",
            "dossier": {},
            "workflow": {},
        }
        out = analyze_opportunity(item)
        self.assertEqual(out["specification_analysis"]["status"], "document_analysis_pending")

    def test_no_document_no_detail_is_explicitly_missing(self):
        out = analyze_opportunity({"dossier": {}, "workflow": {}})
        self.assertEqual(out["specification_analysis"]["status"], "source_detail_missing")
        self.assertIsNone(out["specification_analysis"]["source_excerpt"])

    def test_eligibility_and_award_fields_remain_distinct(self):
        item = {
            "selection-criteria": "Minimum five years relevant experience",
            "award-criteria": "Price 60%, quality 40%",
            "dossier": {},
            "workflow": {},
        }
        out = analyze_opportunity(item)
        self.assertEqual(out["specification_analysis"]["eligibility_evidence"][0]["field"], "selection-criteria")
        self.assertEqual(out["specification_analysis"]["award_evidence"][0]["field"], "award-criteria")

    def test_free_text_quantity_is_candidate_evidence_not_normalized_fact(self):
        item = {
            "description-lot": "The buyer expects delivery of 5,000 units over twelve months.",
            "dossier": {},
            "workflow": {},
        }
        out = analyze_opportunity(item)
        evidence = out["specification_analysis"]["quantity_evidence"]
        self.assertEqual(evidence[0]["field"], "source_text_candidate")
        self.assertNotIn("quantity", out)

    def test_payload_reports_analysis_counts(self):
        payload = {
            "opportunities": [
                {"source_url": "https://example.test/tender", "dossier": {}, "workflow": {}},
                {"description-lot": "Technical specification: stainless steel", "dossier": {}, "workflow": {}},
            ]
        }
        out = analyze_payload(payload)
        self.assertEqual(out["specification_analysis"]["mode"], "source_evidence_only")
        self.assertEqual(out["specification_analysis"]["analyzed_count"], 2)
        self.assertEqual(out["specification_analysis"]["document_analysis_pending"], 1)


if __name__ == "__main__":
    unittest.main()
