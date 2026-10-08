import unittest

from src.specification import analyze_opportunity, analyze_payload


class SpecificationEvidenceTests(unittest.TestCase):
    def test_structured_specification_is_sourcing_ready(self):
        item = {
            "technical-specification": "Accuracy 0.1 mg; ISO 9001 certificate required.",
            "quantity-lot": "12",
            "quantity-unit-lot": "pieces",
            "place-of-performance-city-lot": "Bucharest",
            "dossier": {"supplier_sourcing_ready": True, "missing_fields": []},
            "supplier_research": {"status": "source_search_ready", "blocked_by_missing_fields": []},
            "workflow": {"opportunity_dossier": {"status": "ready_for_supplier_research", "missing_fields": []}},
        }
        out = analyze_opportunity(item)
        spec = out["specification_analysis"]
        self.assertEqual(spec["status"], "structured_specification_analyzed")
        self.assertTrue(spec["supplier_sourcing_ready"])
        self.assertEqual(spec["quantity_evidence"][0]["field"], "quantity-lot")
        self.assertIn("ISO 9001", spec["standards"])
        self.assertTrue(out["dossier"]["supplier_sourcing_ready"])
        self.assertEqual(out["supplier_research"]["status"], "source_search_ready")

    def test_pdf_is_marked_for_parser_and_blocks_sourcing(self):
        item = {
            "official_links": ["https://ted.europa.eu/specification.pdf"],
            "dossier": {"supplier_sourcing_ready": True, "missing_fields": []},
            "supplier_research": {"status": "source_search_ready", "blocked_by_missing_fields": []},
            "workflow": {"opportunity_dossier": {"status": "ready_for_supplier_research", "missing_fields": []}},
        }
        out = analyze_opportunity(item)
        spec = out["specification_analysis"]
        self.assertEqual(spec["status"], "document_analysis_pending")
        self.assertTrue(spec["attachment_requires_parsing"])
        self.assertFalse(spec["supplier_sourcing_ready"])
        self.assertEqual(spec["documents"][0]["kind"], "pdf")
        self.assertFalse(spec["technical_evidence"])
        self.assertFalse(out["dossier"]["supplier_sourcing_ready"])
        self.assertEqual(out["supplier_research"]["status"], "specification_review_pending")
        self.assertIn("specification_evidence", out["dossier"]["missing_fields"])

    def test_source_page_without_details_stays_pending_and_blocks_sourcing(self):
        item = {
            "source_url": "https://ted.europa.eu/en/notice/-/detail/123",
            "dossier": {"supplier_sourcing_ready": True},
            "supplier_research": {"status": "source_search_ready"},
            "workflow": {"opportunity_dossier": {"status": "ready_for_supplier_research"}},
        }
        out = analyze_opportunity(item)
        self.assertEqual(out["specification_analysis"]["status"], "document_analysis_pending")
        self.assertFalse(out["dossier"]["supplier_sourcing_ready"])
        self.assertEqual(out["workflow"]["opportunity_dossier"]["status"], "specification_review_pending")

    def test_short_generic_description_is_not_treated_as_specification(self):
        item = {
            "detail_tr": "Laboratuvar ekipmanı satın alınacaktır.",
            "dossier": {"supplier_sourcing_ready": True},
            "supplier_research": {"status": "source_search_ready"},
            "workflow": {"opportunity_dossier": {"status": "ready_for_supplier_research"}},
        }
        out = analyze_opportunity(item)
        self.assertEqual(out["specification_analysis"]["status"], "source_description_insufficient")
        self.assertFalse(out["specification_analysis"]["supplier_sourcing_ready"])
        self.assertFalse(out["dossier"]["supplier_sourcing_ready"])

    def test_substantive_source_description_can_be_ready_with_commercial_evidence(self):
        description = (
            "Technical requirement: laboratory equipment must provide measurement accuracy, "
            "stainless steel construction, defined performance characteristics and compatible accessories. "
            "Delivery shall include 25 units to the buyer facility within sixty days."
        )
        item = {
            "description-lot": description,
            "quantity-lot": "25",
            "dossier": {"supplier_sourcing_ready": True},
            "supplier_research": {"status": "source_search_ready"},
            "workflow": {"opportunity_dossier": {"status": "ready_for_supplier_research"}},
        }
        out = analyze_opportunity(item)
        self.assertEqual(out["specification_analysis"]["status"], "source_description_analyzed")
        self.assertTrue(out["specification_analysis"]["supplier_sourcing_ready"])

    def test_no_document_no_detail_is_explicitly_missing(self):
        out = analyze_opportunity({"dossier": {}, "workflow": {}})
        self.assertEqual(out["specification_analysis"]["status"], "source_detail_missing")
        self.assertIsNone(out["specification_analysis"]["source_excerpt"])
        self.assertFalse(out["specification_analysis"]["supplier_sourcing_ready"])

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
        self.assertFalse(out["specification_analysis"]["supplier_sourcing_ready"])

    def test_payload_reports_analysis_and_readiness_counts(self):
        payload = {
            "opportunities": [
                {"source_url": "https://example.test/tender", "dossier": {}, "workflow": {}},
                {"technical-specification": "Equipment accuracy shall be 0.1 mg.", "dossier": {}, "workflow": {}},
            ]
        }
        out = analyze_payload(payload)
        self.assertEqual(out["specification_analysis"]["mode"], "source_evidence_only")
        self.assertEqual(out["specification_analysis"]["analyzed_count"], 2)
        self.assertEqual(out["specification_analysis"]["document_analysis_pending"], 1)
        self.assertEqual(out["specification_analysis"]["supplier_sourcing_ready"], 1)


if __name__ == "__main__":
    unittest.main()
