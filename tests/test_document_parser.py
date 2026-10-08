import unittest
from unittest.mock import patch

from src import document_parser
from src.specification import analyze_opportunity


class DocumentParserTests(unittest.TestCase):
    def test_only_supported_document_extensions_are_candidates(self):
        item = {
            "official_links": [
                "https://example.com/tender.pdf",
                "https://example.com/info.html",
                "https://example.com/spec.docx",
            ]
        }
        self.assertEqual(
            document_parser._candidate_urls(item),
            ["https://example.com/tender.pdf", "https://example.com/spec.docx"],
        )

    def test_successful_document_text_is_stored_with_source_metadata(self):
        item = {"document_url": "https://example.com/spec.pdf"}
        extracted = (
            "Technical specification: equipment capacity minimum 500 units. "
            "Quantity 20 pieces. Delivery destination Ankara. ISO 9001 certificate required."
        )
        with patch.object(document_parser, "_download", return_value=(b"%PDF-test", "application/pdf", "https://example.com/spec.pdf")), patch.object(document_parser, "_parse", return_value=(extracted, "pdf")):
            document_parser.enrich_opportunity(item)
        self.assertEqual(item["document_extraction"]["status"], "parsed")
        self.assertEqual(item["document_extraction"]["parsed_count"], 1)
        self.assertIn("Technical specification", item["document_extracted_text"])

    def test_parsed_document_can_make_specification_source_backed_and_ready(self):
        item = {
            "document_url": "https://example.com/spec.pdf",
            "document_extracted_text": (
                "Technical specification requires equipment capacity minimum 500 units. "
                "Quantity 20 pieces. Delivery destination Ankara. ISO 9001 certificate required."
            ),
            "document_extraction": {"parsed_count": 1},
        }
        analyze_opportunity(item)
        spec = item["specification_analysis"]
        self.assertEqual(spec["status"], "source_document_analyzed")
        self.assertTrue(spec["supplier_sourcing_ready"])
        self.assertTrue(spec["document_parsed"])
        self.assertIn("ISO 9001", spec["standards"])

    def test_failed_document_does_not_open_sourcing_gate(self):
        item = {
            "document_url": "https://example.com/spec.pdf",
            "document_extraction": {"status": "attempted_no_text", "parsed_count": 0},
        }
        analyze_opportunity(item)
        spec = item["specification_analysis"]
        self.assertEqual(spec["status"], "document_analysis_pending")
        self.assertFalse(spec["supplier_sourcing_ready"])


if __name__ == "__main__":
    unittest.main()
