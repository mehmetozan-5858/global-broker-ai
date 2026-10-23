"""The generic document reader must disclose clipping of merged sources."""
import unittest
from unittest.mock import patch
from src import document_parser


class DocumentMergeTruncationTests(unittest.TestCase):
    def test_multiple_documents_report_shared_budget_clipping(self):
        urls = ["https://example.org/specification.pdf", "https://example.org/annex.pdf"]
        item = {"document_url": urls}
        def fake_try(url, attempts, parts, discovered_from=None):
            parts.append("technical requirements " * 1500)
            attempts.append({"url": url, "status": "parsed", "source": "attachment", "kind": "pdf"})
        with patch.object(document_parser, "_try_attachment", side_effect=fake_try):
            document_parser.enrich_opportunity(item)
        info = item["document_extraction"]
        self.assertTrue(info["text_truncated"])
        self.assertGreater(info["omitted_chars"], 0)
        self.assertEqual(len(item["document_extracted_text"]), document_parser.MAX_EXTRACTED_CHARS)

    def test_short_document_is_not_marked_truncated(self):
        item = {"document_url": "https://example.org/specification.pdf"}
        def fake_try(url, attempts, parts, discovered_from=None):
            parts.append("Short technical specification " * 10)
            attempts.append({"url": url, "status": "parsed", "source": "attachment", "kind": "pdf"})
        with patch.object(document_parser, "_try_attachment", side_effect=fake_try):
            document_parser.enrich_opportunity(item)
        self.assertFalse(item["document_extraction"]["text_truncated"])
        self.assertEqual(item["document_extraction"]["omitted_chars"], 0)


if __name__ == "__main__":
    unittest.main()
