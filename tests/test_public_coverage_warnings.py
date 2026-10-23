"""Customer-safe document coverage warnings in the public feed and portal."""
import unittest
from pathlib import Path
from src.public_opportunity_projection import project_public_opportunity

ROOT = Path(__file__).resolve().parents[1]


class PublicCoverageWarningTests(unittest.TestCase):
    def row(self, reasons):
        return {
            "source": "TED", "publication-number": "123456-2026",
            "title": "Equipment procurement",
            "specification_analysis": {
                "document_coverage_blockers": reasons,
                "technical_evidence": [{"text": "SECRET technical requirements"}],
            },
            "document_extracted_text": "SECRET private text",
            "document_extraction": {"attempts": [{"url": "https://private.example/spec.pdf"}]},
        }

    def test_only_allowed_reason_codes_are_public(self):
        result = project_public_opportunity(self.row([
            "attachment_candidates_skipped", "source_text_truncated",
            "SECRET-internal-reason",
        ]))
        self.assertEqual(result["document_coverage_blockers"], [
            "source_text_truncated", "attachment_candidates_skipped",
        ])
        serialized = str(result)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("private.example", serialized)
        self.assertNotIn("document_extracted_text", result)

    def test_reprojection_preserves_codes_and_completed_row_clears_them(self):
        public = project_public_opportunity(self.row(["source_text_truncated"]))
        self.assertEqual(project_public_opportunity(public)["document_coverage_blockers"],
                         ["source_text_truncated"])
        clean = project_public_opportunity(self.row([]))
        self.assertNotIn("document_coverage_blockers", clean)
        self.assertNotIn("document_coverage_blockers", project_public_opportunity(clean))

    def test_customer_portal_displays_bilingual_warning_without_raw_source(self):
        script = (ROOT / "web/customer-portal.js").read_text(encoding="utf-8")
        self.assertIn("function coverageWarnings(o)", script)
        self.assertIn("source_text_truncated", script)
        self.assertIn("attachment_candidates_skipped", script)
        self.assertIn("Resmî belge metni eksik okundu", script)
        self.assertIn("Official document text is incomplete", script)
        self.assertIn("coverageWarnings(o).forEach", script)


if __name__ == "__main__":
    unittest.main()
