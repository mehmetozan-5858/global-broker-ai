"""Clear official document coverage blocker codes and fresh reevaluation."""
import unittest
from src.specification import analyze_opportunity


class DocumentCoverageReasonTests(unittest.TestCase):
    def item(self, extraction):
        return {
            "technical-specification": "Measurement accuracy 0.1 mg; ISO 9001 required",
            "quantity-lot": "12",
            "document_extraction": extraction,
            "dossier": {}, "supplier_research": {}, "workflow": {},
        }

    def test_truncation_and_skipped_annex_have_distinct_reasons(self):
        item = analyze_opportunity(self.item({
            "text_truncated": True, "omitted_chars": 145,
            "attachment_candidates_omitted": 2,
        }))
        reasons = ["source_text_truncated", "attachment_candidates_skipped"]
        self.assertEqual(item["specification_analysis"]["document_coverage_blockers"], reasons)
        self.assertFalse(item["specification_analysis"]["supplier_sourcing_ready"])
        self.assertTrue(item["specification_analysis"]["document_coverage_message"])
        self.assertEqual(item["dossier"]["document_coverage_blockers"], reasons)
        self.assertEqual(item["supplier_research"]["document_coverage_blockers"], reasons)
        self.assertEqual(item["workflow"]["specification_analysis"]["document_coverage_blockers"], reasons)

    def test_completed_extraction_rechecks_and_clears_coverage_reasons(self):
        item = self.item({"text_truncated": True, "attachment_candidates_omitted": 1})
        analyze_opportunity(item)
        item["document_extraction"] = {"text_truncated": False, "attachment_candidates_omitted": 0}
        analyze_opportunity(item)
        spec = item["specification_analysis"]
        self.assertEqual(spec["document_coverage_blockers"], [])
        self.assertIsNone(spec["document_coverage_message"])
        self.assertTrue(spec["supplier_sourcing_ready"])
        self.assertEqual(spec["status"], "structured_specification_analyzed")
        self.assertEqual(item["dossier"]["document_coverage_blockers"], [])
        self.assertEqual(item["workflow"]["specification_analysis"]["document_coverage_blockers"], [])
        # A previous supplier workflow block stays pending until its own re-evaluation.
        self.assertFalse(item["supplier_research"]["dossier_ready"])


if __name__ == "__main__":
    unittest.main()
