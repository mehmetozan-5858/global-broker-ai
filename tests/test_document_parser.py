import io
import sys
import types
import zipfile
import unittest
from unittest.mock import patch

from src import document_parser
from src.a5_source_terms import extract
from src.specification import analyze_opportunity


class DocumentParserTests(unittest.TestCase):
    def test_html_block_and_table_boundaries_keep_fields_separate(self):
        html = b"<p>Quantity: <b>25</b> pcs</p><table><tr><td>Submission deadline:</td><td>2026-12-01</td></tr></table><div>Payment terms: 30 days<br>Delivery location: Ankara</div>"
        text, _ = document_parser._parse_html_page(html, "https://example.test")
        row = {"document_extracted_text": text}
        extract(row)
        self.assertEqual(row["quantity"], "25 pcs")
        self.assertEqual(row["deadline"], "2026-12-01")
        self.assertEqual(row["payment_terms"], "30 days")
        self.assertEqual(row["delivery_location"], "Ankara")

    def test_html_separate_conflicting_quantities_require_review(self):
        text, _ = document_parser._parse_html_page(b"<p>Quantity: 25 pcs</p><p>Submission deadline: 2026-12-01</p><p>Quantity: 50 pcs</p>", "https://example.test")
        row = {"document_extracted_text": text}
        result = extract(row)
        self.assertNotIn("quantity", row)
        self.assertEqual(result["review_required"]["quantity"], "conflicting_labeled_values")

    def test_plain_text_line_endings_keep_fields_separate(self):
        for encoding in ("utf-8", "utf-16"):
            row = {"document_extracted_text": document_parser._parse_text("Quantity: 25 pcs\r\nSubmission deadline: 2026-12-01".encode(encoding))}
            extract(row)
            self.assertEqual(row["quantity"], "25 pcs")
            self.assertEqual(row["deadline"], "2026-12-01")

    def test_docx_paragraphs_and_run_breaks_keep_fields_separate(self):
        xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Quantity: </w:t></w:r><w:r><w:t>25 pcs</w:t></w:r></w:p><w:p><w:r><w:t>Submission deadline: 2026-12-01</w:t><w:br/><w:t>Payment terms: 30 days</w:t></w:r></w:p></w:body></w:document>'
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("word/document.xml", xml)
        row = {"document_extracted_text": document_parser._parse_docx(data.getvalue())}
        extract(row)
        self.assertEqual(row["quantity"], "25 pcs")
        self.assertEqual(row["deadline"], "2026-12-01")
        self.assertEqual(row["payment_terms"], "30 days")

    def test_pdf_lines_keep_conflicting_quantities_separate(self):
        page = types.SimpleNamespace(extract_text=lambda: "Quantity: 25 pcs\nQuantity: 50 pcs\nSubmission deadline: 2026-12-01")
        module = types.SimpleNamespace(PdfReader=lambda data: types.SimpleNamespace(pages=[page]))
        with patch.dict(sys.modules, {"pypdf": module}):
            text = document_parser._parse_pdf(b"fixture")
        row = {"document_extracted_text": text}
        result = extract(row)
        self.assertNotIn("quantity", row)
        self.assertEqual(result["review_required"]["quantity"], "conflicting_labeled_values")
        self.assertEqual(row["deadline"], "2026-12-01")

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
        page_html = (
            b"<html><body><p>Buyer requests laboratory equipment, quantity 25 units, delivery within 60 days. "
            b"The equipment must meet defined accuracy, capacity and material requirements. The supplier must provide "
            b"ISO 9001 certification, compatible accessories, installation documentation and warranty support.</p>"
            b"<a href='/files/spec.pdf'>Technical specification</a></body></html>"
        )
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

    def test_same_id_and_url_are_refetched_for_amendments(self):
        url = "https://example.com/spec.pdf"
        old_text = "Quantity: 20 pieces. " * 10
        new_text = "Quantity: 25 pieces. " * 10
        previous = {"opportunities": [{"id": "opp-1", "document_url": url,
            "document_extracted_text": old_text,
            "document_extraction": {"status": "parsed", "parsed_count": 1}}]}
        current = {"opportunities": [{"id": "opp-1", "document_url": url}]}
        with patch.object(document_parser, "_download", return_value=(b"%PDF-test", "application/pdf", url)) as download, patch.object(document_parser, "_parse", return_value=(new_text, "pdf")):
            out = document_parser.enrich_payload(current, previous)
        download.assert_called_once()
        row = out["opportunities"][0]
        self.assertEqual(row["document_extracted_text"], new_text)
        self.assertEqual(row["document_extraction"]["refresh_policy"], "every_scan")
        self.assertIn("checked_at", row["document_extraction"])
        self.assertEqual(out["document_extraction"]["reused_last_known_good"], 0)

    def test_failed_refresh_never_restores_old_document_evidence(self):
        old = {"id": "opp-1", "document_url": "https://example.com/spec.pdf",
            "document_extracted_text": "Technical specification ISO 9001 " * 10,
            "document_extraction": {"status": "parsed", "parsed_count": 1}}
        current = {"opportunities": [dict(old)]}
        with patch.object(document_parser, "_download", side_effect=TimeoutError("source unavailable")):
            document_parser.enrich_payload(current, {"opportunities": [old]})
        row = current["opportunities"][0]
        self.assertNotIn("document_extracted_text", row)
        self.assertEqual(row["document_extraction"]["status"], "attempted_no_text")
        self.assertEqual(row["document_extraction"]["parsed_count"], 0)
        self.assertFalse(analyze_opportunity(row)["specification_analysis"]["document_parsed"])

    def test_removed_source_cannot_keep_old_document_evidence(self):
        row = {"id": "opp-1", "document_extracted_text": "Old evidence " * 20,
               "document_extraction": {"status": "parsed", "parsed_count": 1}}
        with patch.object(document_parser, "_download") as download:
            document_parser.enrich_payload({"opportunities": [row]})
        download.assert_not_called()
        self.assertNotIn("document_extracted_text", row)
        self.assertEqual(row["document_extraction"]["status"], "no_supported_document")

    def test_long_portal_cannot_push_discovered_pdf_out_of_text_budget(self):
        item = {"source_url": "https://example.test/tender"}
        page = ("<html><body><p>" + ("Portal listing content. " * 2500) + "</p><a href='/spec.pdf'>PDF</a></body></html>").encode()
        technical = "Technical specification: measurement accuracy must be 0.1 mg. " * 3
        def download(url, max_bytes=document_parser.MAX_DOCUMENT_BYTES):
            return (page, "text/html", url) if url.endswith("/tender") else (b"%PDF-test", "application/pdf", url)
        with patch.object(document_parser, "_download", side_effect=download), patch.object(document_parser, "_parse", return_value=(technical, "pdf")):
            document_parser.enrich_opportunity(item)
        self.assertTrue(item["document_extracted_text"].startswith(technical))
        self.assertLessEqual(len(item["document_extracted_text"]), document_parser.MAX_EXTRACTED_CHARS)
        self.assertTrue(analyze_opportunity(item)["specification_analysis"]["document_parsed"])

    def test_parsed_document_can_make_specification_source_backed_and_ready(self):
        item = {
            "document_url": "https://example.com/spec.pdf",
            "document_extracted_text": (
                "Technical specification requires equipment capacity minimum 500 units. "
                "Quantity 20 pieces. Delivery destination Ankara. ISO 9001 certificate required."
            ),
            "document_extraction": {"parsed_count": 1, "attempts": [{
                "url": "https://example.com/spec.pdf", "source": "attachment", "kind": "pdf", "status": "parsed",
            }]},
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
