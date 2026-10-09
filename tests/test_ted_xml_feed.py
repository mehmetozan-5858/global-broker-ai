import unittest
from unittest.mock import patch

from src import ted_xml_enricher, ted_xml_parser


class TedXmlFeedTests(unittest.TestCase):
    def test_xml_parser_extracts_text_and_attachment(self):
        xml = b"""<?xml version='1.0' encoding='UTF-8'?>
        <Notice xmlns='urn:test'>
          <Title>Supply of laboratory analyzers</Title>
          <Description>Buyer requires 24 analyzers, installation, calibration and ISO 9001 compliant quality controls. Delivery is required within 60 days to the contracting authority warehouse.</Description>
          <Attachment href='https://ted.europa.eu/files/specification.pdf'>Specification</Attachment>
        </Notice>"""
        text, links = ted_xml_parser.parse_ted_xml(xml, "https://ted.europa.eu/en/notice/123/xml")
        self.assertIn("Supply of laboratory analyzers", text)
        self.assertIn("24 analyzers", text)
        self.assertEqual(links, ["https://ted.europa.eu/files/specification.pdf"])

    def test_ted_xml_opportunity_becomes_source_backed(self):
        xml = b"""<?xml version='1.0' encoding='UTF-8'?>
        <Notice><Title>Industrial pump supply</Title><Description>Technical specification requires 50 corrosion resistant industrial pumps, minimum stated flow capacity, CE conformity, ISO 9001 quality system, delivery documentation, spare parts support and delivery within 75 days to the buyer facility.</Description></Notice>"""
        item = {
            "source": "TED",
            "source_url": "https://ted.europa.eu/en/notice/657062-2026/xml",
            "document_extraction": {
                "status": "attempted_no_text",
                "parsed_count": 0,
                "attempts": [{"source": "source_page", "status": "failed", "error": "insufficient_source_page_text"}],
            },
        }
        with patch.object(
            ted_xml_enricher.document_parser,
            "_download",
            return_value=(xml, "application/xml", item["source_url"]),
        ):
            ok = ted_xml_enricher.enrich_opportunity(item)
        self.assertTrue(ok)
        self.assertTrue(item["document_extraction"]["ted_xml_parsed"])
        self.assertEqual(item["document_extraction"]["status"], "parsed")
        self.assertIn("50 corrosion resistant industrial pumps", item["document_extracted_text"])
        self.assertEqual(item["document_extraction"]["parsed_count"], 1)

    def test_short_or_invalid_xml_does_not_open_gate(self):
        item = {"source": "TED", "source_url": "https://ted.europa.eu/en/notice/1/xml"}
        with patch.object(
            ted_xml_enricher.document_parser,
            "_download",
            return_value=(b"<?xml version='1.0'?><Notice><Title>Short</Title></Notice>", "application/xml", item["source_url"]),
        ):
            ok = ted_xml_enricher.enrich_opportunity(item)
        self.assertFalse(ok)
        self.assertEqual(item["document_extraction"]["status"], "attempted_no_text")
        self.assertFalse(item["document_extraction"]["ted_xml_parsed"])

    def test_non_ted_item_is_ignored(self):
        payload = {"opportunities": [{"source": "World Bank", "source_url": "https://example.com/tender"}]}
        out = ted_xml_enricher.enrich_payload(payload)
        self.assertEqual(out["document_extraction"]["ted_xml_attempted"], 0)
        self.assertEqual(out["document_extraction"]["ted_xml_parsed"], 0)


if __name__ == "__main__":
    unittest.main()
