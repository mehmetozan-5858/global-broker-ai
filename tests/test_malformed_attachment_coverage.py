"""Fail-closed coverage metadata on the official-document supplier gate."""
import unittest
from src.specification import analyze_opportunity


class MalformedAttachmentCoverageTests(unittest.TestCase):
    def item(self, count):
        return {
            "technical-specification": "Measurement accuracy 0.1 mg ISO 9001",
            "quantity-lot": "12",
            "document_extraction": {"attachment_candidates_omitted": count},
            "dossier": {"supplier_sourcing_ready": True},
            "supplier_research": {"dossier_ready": True},
            "workflow": {},
        }

    def test_untrusted_counts_cannot_crash_scan_or_unlock_supplier(self):
        invalid = ("unavailable", "-1", -1, 1.5, True, False, {}, [],
                   "9" * 10000)
        for count in invalid:
            with self.subTest(kind=type(count).__name__, short=str(count)[:25]):
                item = analyze_opportunity(self.item(count))
                self.assertFalse(item["specification_analysis"]["supplier_sourcing_ready"])
                self.assertIn("attachment_candidates_skipped",
                              item["specification_analysis"]["document_coverage_blockers"])
                self.assertFalse(item["supplier_research"]["dossier_ready"])
                self.assertFalse(item["dossier"]["supplier_sourcing_ready"])

    def test_legitimate_zero_and_positive_counts_remain_compatible(self):
        for count, omitted in ((None, 0), (0, 0), ("0", 0), (2, 2), ("2", 2)):
            with self.subTest(count=count):
                item = analyze_opportunity(self.item(count))
                analysis = item["specification_analysis"]
                self.assertEqual(analysis["attachment_candidates_omitted"], omitted)
                self.assertEqual(analysis["supplier_sourcing_ready"], omitted == 0)
                self.assertEqual(analysis["document_coverage_incomplete"], omitted != 0)


if __name__ == "__main__":
    unittest.main()
