import unittest
from unittest.mock import patch
from src.ted_xml_enricher import enrich_opportunity

class TedAttachmentEvidenceTests(unittest.TestCase):
    def test_ted_xml_discovered_attachment_is_read_and_recorded(self):
        item={"source":"TED","official_links":["https://ted.europa.eu/en/notice/660580-2026/xml"]}
        xml=b"<?xml version='1.0'?><notice><description>"+b"Procurement of medical goods and equipment. "*12+b"</description><document>https://public.example.org/terms.pdf</document></notice>"
        def fake_attachment(url,attempts,parts,discovered_from=None):
            parts.append("Tender participation requires the documented certification and evidence.")
            attempts.append({"url":url,"status":"parsed","source":"attachment","discovered_from":discovered_from})
        with patch("src.document_parser._download",return_value=(xml,"application/xml","https://ted.europa.eu/en/notice/660580-2026/xml")),patch("src.document_parser._try_attachment",side_effect=fake_attachment) as reader:
            self.assertTrue(enrich_opportunity(item))
        reader.assert_called_once()
        self.assertIn("documented certification",item["document_extracted_text"])
        self.assertEqual(item["document_extraction"]["parsed_count"],2)
        self.assertTrue(any(a.get("discovered_from")=="https://ted.europa.eu/en/notice/660580-2026/xml" for a in item["document_extraction"]["attempts"]))

if __name__=="__main__":
    unittest.main()
