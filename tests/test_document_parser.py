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
        self.assertEqual(document_parser._source_page_urls(item), ["https://example.com/info.html"])

    def test_html_page_extracts_visible_text_and_relative_attachment(self):
        html = b"""<html><body><h1>Laboratory equipment tender</h1><p>Technical specification requires 25 units with ISO 9001 certification and delivery within 60 days.</p><a href='/files/spec.pdf'>Specification PDF</a><script>ignore me</script></body></html>"""
        text, links = document_parser._parse_html_page(html, "https://example.com/tenders/123")
        self.assertIn("Laboratory equipment tender", text)
        self.assertNotIn("ignore me", text)
        self.assertEqual(links, ["https://example.com/files/spec.pdf"])

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

    def test_source_page_discovers_and_parses_attachment(self):
        item = {"source_url": "https://example.com/tenders/123"}
        page_html = b"<html><body><p>Buyer requests laboratory equipment, quantity 25 units, delivery within 60 days.</p><a href='/files/spec.pdf'>Technical specification</a></body></html>"
        pdf_text = (
            "Technical specification requires equipment capacity minimum 500 units. "
            "Quantity 25 pieces. Delivery destination Ankara. ISO 9001 certificate required."
        )

        def fake_download(url, max_bytes=document_parser.MAX_DOCUMENT_BYTES):
            if url.endswith("/tenders/123"):
                return page_html, "text/html", url
            if url.endswith("/files/spec.pdf"):
                return b"%PDF-test", "application/pdf", url
            raise AssertionError(url)

        with patch.object(document_parser, "_download", side_effect=fake_download), patch.object(document_parser, "_parse", return_value=(pdf_text, "pdf")):
            document_parser.enrich_opportunity(item)
        info = item["document_extraction"]
        self.assertEqual(info["source_page_count"], 1)
        self.assertEqual(info["discovered_attachment_count"], 1)
        self.assertEqual(info["parsed_count"], 2)
        self.assertIn("Technical specification", item["document_extracted_text"])

    def test_last_good_extraction_is_reused_without_network(self):
        current = {"opportunities": [{"id": "opp-1", "source_url": "https://example.com/tender"}]}
        previous = {
            "opportunities": [{
                "id": "opp-1",
                "document_extracted_text": "Technical specification " + ("x" * 120),
                "document_extraction": {"status": "parsed", "parsed_count": 1, "candidate_count": 1},
            }]
        }
        with patch.object(document_parser, "enrich_opportunity") as enrich:
            out = document_parser.enrich_payload(current, previous)
        enrich.assert_not_called()
        self.assertTrue(out["opportunities"][0]["document_extraction"]["reused_from_last_known_good"])
        self.assertEqual(out["document_extraction"]["reused_last_known_good"], 1)

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
