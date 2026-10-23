"""Well-formed XML error payloads must not masquerade as TED notices."""
import unittest
from src.ted_xml_parser import parse_ted_xml


class TEDXMLNoticeRootTests(unittest.TestCase):
    URL = "https://ted.europa.eu/en/notice/681487-2026/xml"

    def test_error_envelope_rejected(self):
        with self.assertRaisesRegex(ValueError, "ted_xml_notice_root_missing"):
            parse_ted_xml(b"<Error><Message>Request rejected</Message></Error>", self.URL)

    def test_generic_feed_rejected(self):
        with self.assertRaisesRegex(ValueError, "ted_xml_notice_root_missing"):
            parse_ted_xml(b"<feed><entry>Not a notice</entry></feed>", self.URL)

    def test_namespaced_notice_allowed(self):
        text, links = parse_ted_xml(
            b'<Notice xmlns="urn:test"><Title>Industrial pumps</Title></Notice>', self.URL
        )
        self.assertIn("Industrial pumps", text)
        self.assertEqual(links, [])


if __name__ == "__main__":
    unittest.main()
