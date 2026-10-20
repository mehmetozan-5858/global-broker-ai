import unittest

from src.specification import analyze_opportunity, analyze_payload


class SpecificationEvidenceTests(unittest.TestCase):
    def extracted_item(self, attempts):
        return {
            "source_url": "https://example.test/tender",
            "document_extracted_text": (
                "Technical equipment requirements include minimum capacity, measurement accuracy, "
                "stainless steel material and compatible accessories. Delivery of 25 units is required."
            ),
            "document_extraction": {"parsed_count": sum(a.get("status") == "parsed" for a in attempts), "attempts": attempts},
            "dossier": {}, "workflow": {},
        }

    def test_page_read_is_not_a_parsed_attachment(self):
        item = self.extracted_item([{"url": "https://example.test/tender", "kind": "source_page", "status": "parsed"}])
        item["document_url"] = "https://example.test/spec.pdf"
        spec = analyze_opportunity(item)["specification_analysis"]
        self.assertFalse(spec["document_parsed"])
        self.assertTrue(spec["source_page_parsed"])
        self.assertEqual(spec["status"], "source_page_analyzed")
        self.assertTrue(spec["attachment_requires_parsing"])
        self.assertEqual(spec["unparsed_attachment_count"], 1)

    def test_discovered_pdf_is_retained_in_private_specification_links(self):
        item = self.extracted_item([{"url": "https://example.test/files/spec.pdf", "kind": "pdf", "status": "parsed"}])
        spec = analyze_opportunity(item)["specification_analysis"]
        self.assertTrue(spec["document_parsed"])
        self.assertEqual(spec["parsed_document_count"], 1)
        self.assertIn({"url": "https://example.test/files/spec.pdf", "kind": "pdf", "parse_status": "parsed"}, spec["documents"])
        self.assertEqual(item["dossier"]["document_links"], spec["documents"])

    def test_one_good_pdf_does_not_mark_failed_attachment_complete(self):
        item = self.extracted_item([
            {"url": "https://example.test/good.pdf", "kind": "pdf", "status": "parsed"},
            {"url": "https://example.test/missing.pdf", "status": "failed"},
        ])
        spec = analyze_opportunity(item)["specification_analysis"]
        self.assertTrue(spec["document_parsed"])
        self.assertTrue(spec["attachment_requires_parsing"])
        self.assertTrue(item["workflow"]["specification_analysis"]["attachment_requires_parsing"])
        self.assertEqual(spec["unparsed_attachment_count"], 1)

    def test_dynamic_pdf_uses_parser_kind_and_deduplicates_redirect(self):
        item = self.extracted_item([{"url": "https://example.test/download?id=5", "final_url": "https://example.test/content/5", "kind": "pdf", "status": "parsed"}])
        item["document_url"] = "https://example.test/download?id=5"
        spec = analyze_opportunity(item)["specification_analysis"]
        self.assertEqual(spec["parsed_document_count"], 1)
        self.assertEqual(sum(d["kind"] == "pdf" for d in spec["documents"]), 1)
        self.assertFalse(spec["attachment_requires_parsing"])

    def test_legacy_total_without_provenance_does_not_prove_pdf_read(self):
        item = self.extracted_item([])
        item["document_url"] = "https://example.test/spec.pdf"
        item["document_extraction"] = {"parsed_count": 1}
        spec = analyze_opportunity(item)["specification_analysis"]
        self.assertFalse(spec["document_parsed"])
        self.assertFalse(spec["supplier_sourcing_ready"])

    def test_pdf_url_returning_html_does_not_count_as_pdf(self):
        item = self.extracted_item([{"url": "https://example.test/spec.pdf", "kind": "source_page", "status": "parsed"}])
        spec = analyze_opportunity(item)["specification_analysis"]
        self.assertFalse(spec["document_parsed"])
        self.assertTrue(spec["attachment_requires_parsing"])

    def test_payload_separates_page_and_document_counts(self):
        page = self.extracted_item([{"url": "https://example.test/tender", "kind": "source_page", "status": "parsed"}])
        pdf = self.extracted_item([{"url": "https://example.test/spec.pdf", "kind": "pdf", "status": "parsed"}])
        result = analyze_payload({"opportunities": [page, pdf]})["specification_analysis"]
        self.assertEqual(result["parsed_document_opportunities"], 1)
        self.assertEqual(result["parsed_source_page_opportunities"], 1)
        self.assertEqual(result["parsed_attachments"], 1)

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
        self.assertEqual(out["specification_analysis"]["mode"], "source_evidence_plus_public_documents")
        self.assertEqual(out["specification_analysis"]["analyzed_count"], 2)
        self.assertEqual(out["specification_analysis"]["document_analysis_pending"], 1)
        self.assertEqual(out["specification_analysis"]["supplier_sourcing_ready"], 1)


if __name__ == "__main__":
    unittest.main()
