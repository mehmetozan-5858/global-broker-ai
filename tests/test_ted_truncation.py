"""TED extraction must report incomplete text without claiming full specifications."""
import unittest
from unittest.mock import patch
from src import document_parser, ted_xml_enricher

PUBLICATION = "123456-2026"
URL = f"https://ted.europa.eu/en/notice/{PUBLICATION}/xml"


class TedTruncationTests(unittest.TestCase):
    def test_long_notice_is_explicitly_marked_truncated(self):
        xml = ("<notice><description>" + ("technical requirement " * 3000) + "</description></notice>").encode()
        row = {"source": "TED", "publication-number": PUBLICATION}
        with patch.object(document_parser, "_download", return_value=(xml, "application/xml", URL)):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(row))
        info = row["document_extraction"]
        self.assertTrue(info["text_truncated"])
        self.assertGreater(info["omitted_chars"], 0)
        self.assertEqual(len(row["document_extracted_text"]), document_parser.MAX_EXTRACTED_CHARS)

    def test_short_notice_is_not_marked_truncated(self):
        xml = ("<notice><description>" + ("technical requirement " * 15) + "</description></notice>").encode()
        row = {"source": "TED", "publication-number": PUBLICATION}
        with patch.object(document_parser, "_download", return_value=(xml, "application/xml", URL)):
            self.assertTrue(ted_xml_enricher.enrich_opportunity(row))
        self.assertFalse(row["document_extraction"]["text_truncated"])
        self.assertEqual(row["document_extraction"]["omitted_chars"], 0)


if __name__ == "__main__":
    unittest.main()
