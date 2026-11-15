"""Incomplete official document coverage must not be treated as sourcing-ready."""
import unittest
from src.specification import analyze_opportunity


class SpecificationCoverageGateTests(unittest.TestCase):
    def item(self, extraction):
        return {
            "technical-specification": "Equipment accuracy 0.1 mg, ISO 9001 certificate required",
            "quantity-lot": "12",
            "document_extraction": extraction,
            "dossier": {"supplier_sourcing_ready": True, "missing_fields": []},
            "supplier_research": {"status": "source_search_ready", "dossier_ready": True},
            "workflow": {"opportunity_dossier": {"status": "ready_for_supplier_research"}},
        }

    def test_clipped_text_blocks_supplier_sourcing_even_with_structured_fields(self):
        item = analyze_opportunity(self.item({"text_truncated": True, "omitted_chars": 25}))
        self.assertEqual(item["specification_analysis"]["status"], "document_coverage_incomplete")
        self.assertFalse(item["specification_analysis"]["supplier_sourcing_ready"])
        self.assertTrue(item["specification_analysis"]["text_truncated"])
        self.assertFalse(item["dossier"]["supplier_sourcing_ready"])
        self.assertFalse(item["supplier_research"]["dossier_ready"])
        self.assertEqual(item["workflow"]["opportunity_dossier"]["status"], "specification_review_pending")

    def test_skipped_annex_blocks_sourcing_and_reports_count(self):
        item = analyze_opportunity(self.item({"text_truncated": False, "attachment_candidates_omitted": 2}))
        self.assertTrue(item["specification_analysis"]["document_coverage_incomplete"])
        self.assertEqual(item["specification_analysis"]["attachment_candidates_omitted"], 2)
        self.assertFalse(item["specification_analysis"]["supplier_sourcing_ready"])
        self.assertIn("specification_evidence", item["dossier"]["missing_fields"])

    def test_complete_document_coverage_preserves_existing_structured_readiness(self):
        item = analyze_opportunity(self.item({"text_truncated": False, "attachment_candidates_omitted": 0}))
        self.assertEqual(item["specification_analysis"]["status"], "structured_specification_analyzed")
        self.assertTrue(item["specification_analysis"]["supplier_sourcing_ready"])
        self.assertFalse(item["specification_analysis"]["document_coverage_incomplete"])

    def test_replacing_partial_source_does_not_restore_stale_supplier_or_workflow_approval(self):
        for extraction in ({'text_truncated': True},
                           {'attachment_candidates_omitted': 2},
                           {'attachment_candidates_failed': 1},
                           {'document_versions_review_required': True}):
            with self.subTest(extraction=extraction):
                item = analyze_opportunity(self.item(extraction))
                self.assertFalse(item['dossier']['supplier_sourcing_ready'])
                self.assertFalse(item['supplier_research']['dossier_ready'])
                # Fresh complete source permits specification analysis only.
                # Dossier/supplier re-review remains necessary after a denial.
                item['document_extraction'] = {'text_truncated': False,
                                               'attachment_candidates_omitted': 0}
                analyze_opportunity(item)
                self.assertTrue(item['specification_analysis']['supplier_sourcing_ready'])
                self.assertFalse(item['dossier']['supplier_sourcing_ready'])
                self.assertFalse(item['supplier_research']['dossier_ready'])
                self.assertEqual(item['workflow']['opportunity_dossier']['status'],
                                 'specification_review_pending')


if __name__ == "__main__":
    unittest.main()
